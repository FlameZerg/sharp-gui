import os
import platform
import subprocess


def browse_folder_native(title, initial_dir):
    """调用系统原生文件夹选择对话框。"""
    if not os.path.isdir(initial_dir):
        initial_dir = os.path.expanduser("~")

    system = platform.system()

    try:
        if system == "Linux":
            try:
                result = subprocess.run(
                    [
                        "zenity",
                        "--file-selection",
                        "--directory",
                        "--title=" + title,
                        "--filename=" + initial_dir + "/",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=120,
                )
                if result.returncode == 0 and result.stdout.strip():
                    return {"success": True, "path": result.stdout.strip()}, 200
                if result.returncode == 1:
                    return {"success": False, "cancelled": True}, 200
            except FileNotFoundError:
                try:
                    result = subprocess.run(
                        ["kdialog", "--getexistingdirectory", initial_dir, "--title", title],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    if result.returncode == 0 and result.stdout.strip():
                        return {"success": True, "path": result.stdout.strip()}, 200
                except FileNotFoundError:
                    pass

        elif system == "Darwin":
            script = f'''
            tell application "System Events"
                activate
                set folderPath to choose folder with prompt "{title}" default location POSIX file "{initial_dir}"
                return POSIX path of folderPath
            end tell
            '''
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return {"success": True, "path": result.stdout.strip().rstrip("/")}, 200
            if result.returncode != 0:
                return {"success": False, "cancelled": True}, 200

        elif system == "Windows":
            script = f'''
            Add-Type -AssemblyName System.Windows.Forms
            $browser = New-Object System.Windows.Forms.FolderBrowserDialog
            $browser.Description = "{title}"
            $browser.SelectedPath = "{initial_dir}"
            $browser.ShowNewFolderButton = $true
            if ($browser.ShowDialog() -eq "OK") {{
                Write-Output $browser.SelectedPath
            }}
            '''
            result = subprocess.run(
                ["powershell", "-Command", script],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode == 0 and result.stdout.strip():
                return {"success": True, "path": result.stdout.strip()}, 200

        return {
            "success": False,
            "error": "No dialog tool available. Please enter path manually.",
        }, 500

    except subprocess.TimeoutExpired:
        return {"success": False, "cancelled": True}, 200
    except Exception as exc:
        return {"success": False, "error": str(exc)}, 500
