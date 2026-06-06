import os
import queue
import subprocess
import threading
import time
import traceback
import uuid

from backend import runtime
from backend.services.model_convert import ply_to_spz

TASK_RETENTION_SECONDS = 3600
CLEANUP_INTERVAL = 300


class TaskManager:
    def __init__(
        self,
        *,
        paths,
        thumbnail_generator=None,
        sharp_device_selector=None,
        sharp_command_resolver=None,
        spz_converter=None,
        verbose_log=None,
        cleanup_interval=CLEANUP_INTERVAL,
        retention_seconds=TASK_RETENTION_SECONDS,
    ):
        self.paths = paths
        self.thumbnail_generator = thumbnail_generator
        self.sharp_device_selector = sharp_device_selector or runtime.select_sharp_device
        self.sharp_command_resolver = sharp_command_resolver or runtime.resolve_sharp_command
        self.spz_converter = spz_converter or ply_to_spz
        self.verbose_log = verbose_log or runtime.verbose_log
        self.cleanup_interval = cleanup_interval
        self.retention_seconds = retention_seconds

        self.task_queue = queue.Queue()
        self.task_status = {}
        self.task_lock = threading.Lock()
        self.running_processes = {}
        self._workers_started = False
        self._cleanup_started = False
        self._start_lock = threading.Lock()

    def set_thumbnail_generator(self, thumbnail_generator):
        self.thumbnail_generator = thumbnail_generator

    def enqueue_file(self, input_path, filename):
        if self.thumbnail_generator:
            self.thumbnail_generator(input_path, filename)

        task_id = str(uuid.uuid4())
        task_info = {
            "id": task_id,
            "status": "pending",
            "filename": filename,
            "input_path": input_path,
            "output_folder": self.paths.output_folder,
            "created_at": time.time(),
            "error": None,
        }

        with self.task_lock:
            self.task_status[task_id] = task_info
        self.task_queue.put(task_id)
        return task_info

    def list_tasks(self):
        with self.task_lock:
            tasks = list(self.task_status.values())
        tasks.sort(key=lambda x: x["created_at"], reverse=True)
        has_active = any(t["status"] in ("pending", "processing") for t in tasks)
        return tasks, has_active

    def cancel_task(self, task_id):
        with self.task_lock:
            task = self.task_status.get(task_id)
            if not task:
                return {"success": False, "error": "Task not found"}, 404

            if task["status"] == "pending":
                task["status"] = "cancelled"
                return {"success": True, "message": "Task cancelled"}, 200

            if task["status"] == "processing":
                task["status"] = "cancelled"
                process = self.running_processes.get(task_id)
                if process:
                    try:
                        process.terminate()
                    except Exception:
                        pass
                return {"success": True, "message": "Task cancellation requested"}, 200

            return {"success": False, "error": f"Task already {task['status']}"}, 400

    def cleanup_old_tasks(self):
        """定期清理已完成的旧任务，防止内存泄漏。"""
        while True:
            time.sleep(self.cleanup_interval)
            cutoff = time.time() - self.retention_seconds
            with self.task_lock:
                old_ids = [
                    task_id for task_id, task in self.task_status.items()
                    if task["created_at"] < cutoff and task["status"] in ("completed", "failed")
                ]
                for task_id in old_ids:
                    del self.task_status[task_id]
                if old_ids:
                    print(f"🧹 Cleaned up {len(old_ids)} old tasks")

    def worker(self):
        """后台工作线程，持续处理队列中的任务。"""
        print("👷 Worker thread started...")
        while True:
            task_id = self.task_queue.get()
            if task_id is None:
                break

            with self.task_lock:
                task = self.task_status.get(task_id)
                if not task or task["status"] == "cancelled":
                    self.task_queue.task_done()
                    continue
                input_path = task["input_path"]
                output_folder = task["output_folder"]
                filename = task["filename"]

            print(f"🔄 Processing task {task_id}: {filename}")
            with self.task_lock:
                self.task_status[task_id]["status"] = "processing"
                self.task_status[task_id]["progress"] = 0
                self.task_status[task_id]["stage"] = "starting"

            device = self.sharp_device_selector()
            print(f"Using Sharp device: {device}")
            sharp_command = self.sharp_command_resolver()
            print(f"Using Sharp command: {sharp_command}")

            cmd = [
                sharp_command,
                "predict",
                "-i",
                input_path,
                "-o",
                output_folder,
                "--device",
                device,
            ]

            process = None
            try:
                process_env = os.environ.copy()
                process_env.setdefault("PYTHONUTF8", "1")
                process_env.setdefault("PYTHONIOENCODING", "utf-8")
                self.verbose_log(f"Task {task_id} input_path={input_path} exists={os.path.exists(input_path)}")
                self.verbose_log(f"Task {task_id} output_folder={output_folder} exists={os.path.exists(output_folder)}")
                self.verbose_log(f"Task {task_id} command={runtime.format_command_for_log(cmd)}")
                self.verbose_log(f"Task {task_id} subprocess_cwd={os.getcwd()}")
                self.verbose_log(f"Task {task_id} subprocess_path={process_env.get('PATH', '')}")

                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    bufsize=1,
                    env=process_env,
                )

                with self.task_lock:
                    self.running_processes[task_id] = process

                output_lines = []
                cancelled = False
                for line in iter(process.stdout.readline, ""):
                    if not line:
                        break

                    with self.task_lock:
                        if self.task_status.get(task_id, {}).get("status") == "cancelled":
                            cancelled = True
                            break

                    output_lines.append(line)
                    self._update_progress_from_line(task_id, filename, line)

                if cancelled:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except Exception:
                        process.kill()
                    print(f"🛑 Task {task_id} cancelled by user.")
                    self.task_queue.task_done()
                    continue

                process.stdout.close()
                return_code = process.wait()
                self._finish_process(task_id, filename, output_folder, return_code, output_lines)

            except Exception as exc:
                error_text = traceback.format_exc() if runtime.SHARP_VERBOSE else str(exc)
                with self.task_lock:
                    if self.task_status.get(task_id, {}).get("status") != "cancelled":
                        self.task_status[task_id]["status"] = "failed"
                        self.task_status[task_id]["error"] = error_text
                print(f"❌ Task {task_id} exception: {exc}")
                if runtime.SHARP_VERBOSE:
                    print("[DEBUG] Full task exception traceback:", flush=True)
                    print(error_text, flush=True)
            finally:
                with self.task_lock:
                    self.running_processes.pop(task_id, None)

            self.task_queue.task_done()

    def _update_progress_from_line(self, task_id, filename, line):
        line_lower = line.lower()
        with self.task_lock:
            if "downloading" in line_lower or "download" in line_lower:
                self.task_status[task_id]["progress"] = 5
                self.task_status[task_id]["stage"] = "downloading"
            elif "loading checkpoint" in line_lower:
                self.task_status[task_id]["progress"] = 10
                self.task_status[task_id]["stage"] = "loading"
            elif "processing" in line_lower and filename.split(".")[0].lower() in line_lower:
                self.task_status[task_id]["progress"] = 15
                self.task_status[task_id]["stage"] = "processing"
            elif "preprocessing" in line_lower:
                self.task_status[task_id]["progress"] = 25
                self.task_status[task_id]["stage"] = "preprocessing"
            elif "inference" in line_lower:
                self.task_status[task_id]["progress"] = 50
                self.task_status[task_id]["stage"] = "inference"
            elif "postprocessing" in line_lower:
                self.task_status[task_id]["progress"] = 80
                self.task_status[task_id]["stage"] = "postprocessing"
            elif "saving" in line_lower:
                self.task_status[task_id]["progress"] = 95
                self.task_status[task_id]["stage"] = "saving"

    def _finish_process(self, task_id, filename, output_folder, return_code, output_lines):
        if return_code == 0:
            name_without_ext = os.path.splitext(filename)[0]
            expected_ply = os.path.join(output_folder, name_without_ext + ".ply")

            ply_exists = os.path.exists(expected_ply)
            with self.task_lock:
                if ply_exists:
                    self.task_status[task_id]["status"] = "completed"
                    self.task_status[task_id]["progress"] = 100
                    self.task_status[task_id]["stage"] = "done"
                    print(f"✅ Task {task_id} completed successfully.")
                else:
                    self.task_status[task_id]["status"] = "failed"
                    self.task_status[task_id]["error"] = "Output file not found after execution."
                    print(f"❌ Task {task_id} failed: Output missing.")

            if ply_exists:
                try:
                    spz_result = self.spz_converter(expected_ply)
                    if spz_result:
                        ply_size = os.path.getsize(expected_ply)
                        spz_size = os.path.getsize(spz_result)
                        ratio = 100 - spz_size * 100 // ply_size if ply_size > 0 else 0
                        print(f"📦 SPZ converted: {ply_size/1024:.0f}KB → {spz_size/1024:.0f}KB ({ratio}% smaller)")
                except Exception as exc:
                    print(f"⚠️ SPZ auto-convert failed for {name_without_ext}: {exc}")
            return

        stderr_output = "".join(output_lines)
        with self.task_lock:
            if self.task_status.get(task_id, {}).get("status") != "cancelled":
                self.task_status[task_id]["status"] = "failed"
                self.task_status[task_id]["error"] = stderr_output if stderr_output else "Unknown error"
        print(f"❌ Task {task_id} failed with return code {return_code}")
        if stderr_output:
            print(f"   Error output:\n{stderr_output}")

    def start_workers(self):
        """Start worker and cleanup threads once."""
        with self._start_lock:
            if not self._workers_started:
                threading.Thread(target=self.worker, daemon=True).start()
                self._workers_started = True
            if not self._cleanup_started:
                threading.Thread(target=self.cleanup_old_tasks, daemon=True).start()
                self._cleanup_started = True

    @property
    def workers_started(self):
        return self._workers_started
