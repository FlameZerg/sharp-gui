import { useCallback, useEffect, useState } from 'react';

import { useTranslation } from 'react-i18next';
import { useShallow } from 'zustand/react/shallow';

import { ApiError, fetchAuthStatus, fetchGallery, fetchSettings, fetchTasks, generateFromImages } from '@/api';
import { AccessGate, AccessSetupPrompt } from '@/components/auth';
import { GalleryList } from '@/components/gallery';
import { ImageViewer, Loading } from '@/components/common';
import { ParticleBackground } from '@/components/common/ParticleBackground';
import { Settings, Sidebar } from '@/components/layout';
import { Help } from '@/components/layout/Help/Help';
import { PhotoAlbumList, PhotoGalleryView } from '@/components/photoGallery';
import { useTaskQueue } from '@/hooks/useTaskQueue';
import { useAppStore } from '@/store';
import { ViewerCanvas } from '@/components/viewer/ViewerCanvas/ViewerCanvas';

import './App.css';

const ACCESS_SETUP_PROMPT_SUPPRESSED_KEY = 'sharp-access-setup-prompt-suppressed';

function shouldShowAccessSetupPrompt(status: {
  is_owner: boolean;
  setup_recommended: boolean;
}) {
  if (!status.is_owner || !status.setup_recommended) {
    return false;
  }

  try {
    return localStorage.getItem(ACCESS_SETUP_PROMPT_SUPPRESSED_KEY) !== '1';
  } catch {
    return true;
  }
}

function App() {
  const { t } = useTranslation();
  const [showAccessSetupPrompt, setShowAccessSetupPrompt] = useState(false);
  const { 
    isBooting, 
    bootError,
    isLoading,
    loadingText,
    loadingProgress,
    sidebarCollapsed,
    activeView,
    authStatus,
    isAuthenticated,
    isOwnerAccess,
    setBootComplete, 
    setBootError,
    setAuthStatus,
    setGalleryItems,
    setTasks,
    setLocalAccess,
    setLoading,
    currentModelUrl,
    toggleSidebar,
    setServerModelFormat,
    setCurrentModel,
    setAuthPermissionError,
    setSettingsModalOpen,
  } = useAppStore(
    useShallow((state) => ({
      isBooting: state.isBooting,
      bootError: state.bootError,
      isLoading: state.isLoading,
      loadingText: state.loadingText,
      loadingProgress: state.loadingProgress,
      sidebarCollapsed: state.sidebarCollapsed,
      activeView: state.activeView,
      authStatus: state.authStatus,
      isAuthenticated: state.isAuthenticated,
      isOwnerAccess: state.isOwnerAccess,
      setBootComplete: state.setBootComplete,
      setBootError: state.setBootError,
      setAuthStatus: state.setAuthStatus,
      setGalleryItems: state.setGalleryItems,
      setTasks: state.setTasks,
      setLocalAccess: state.setLocalAccess,
      setLoading: state.setLoading,
      currentModelUrl: state.currentModelUrl,
      toggleSidebar: state.toggleSidebar,
      setServerModelFormat: state.setServerModelFormat,
      setCurrentModel: state.setCurrentModel,
      setAuthPermissionError: state.setAuthPermissionError,
      setSettingsModalOpen: state.setSettingsModalOpen,
    })),
  );

  const loadPrivateData = useCallback(async () => {
    const gallery = await fetchGallery();
    setGalleryItems(gallery);

    const tasksData = await fetchTasks();
    setTasks(tasksData.tasks, tasksData.has_active);

    const settings = await fetchSettings();
    setLocalAccess(settings.is_local ?? false);
    if (settings.model_format) {
      setServerModelFormat(settings.model_format);
    }
  }, [setGalleryItems, setTasks, setLocalAccess, setServerModelFormat]);

  useEffect(() => {
    async function init() {
      try {
        const status = await fetchAuthStatus();
        setAuthStatus(status);

        if (!status.authenticated && !status.is_owner) {
          setBootComplete();
          return;
        }

        await loadPrivateData();
        setShowAccessSetupPrompt(shouldShowAccessSetupPrompt(status));
        setBootComplete();
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) {
          const status = await fetchAuthStatus();
          setAuthStatus(status);
          setBootComplete();
          return;
        }
        const message = error instanceof Error ? error.message : 'Unknown error';
        setBootError(message);
      }
    }
    init();
  }, [loadPrivateData, setAuthStatus, setBootComplete, setBootError]);

  const dismissAccessSetupPrompt = useCallback(() => {
    setShowAccessSetupPrompt(false);
  }, []);

  const suppressAccessSetupPrompt = useCallback(() => {
    try {
      localStorage.setItem(ACCESS_SETUP_PROMPT_SUPPRESSED_KEY, '1');
    } catch {
      // Ignore storage errors and still dismiss for the current render tree.
    }
    setShowAccessSetupPrompt(false);
  }, []);

  const openAccessSettings = useCallback(() => {
    dismissAccessSetupPrompt();
    setSettingsModalOpen(true);
  }, [dismissAccessSetupPrompt, setSettingsModalOpen]);

  // Handle file upload
  const handleUpload = useCallback(async (files: FileList) => {
    try {
      setLoading(true, t('uploadingFiles', { count: files.length }));
      const result = await generateFromImages(files);
      setLoading(false);
      
      if (result.success && result.tasks) {
        setTasks(result.tasks, true);
      }
    } catch (error) {
      setLoading(false);
      const message = error instanceof Error ? error.message : 'Unknown error';
      if (error instanceof ApiError && error.status === 403) {
        setAuthPermissionError(t('ownerOnlyAction'));
        alert(t('ownerOnlyAction'));
        return;
      }
      alert(`${t('uploadFailed')}: ${message}`);
    }
  }, [t, setAuthPermissionError, setLoading, setTasks]);

  // Handle model file drop (.ply / .splat / .spz / .rad) for direct preview
  const handleModelDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    const files = e.dataTransfer?.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    const name = file.name.toLowerCase();
    
    // Check for supported model formats and extract format
    let format: 'ply' | 'splat' | 'spz' | 'rad' | null = null;
    if (name.endsWith('.ply')) {
      format = 'ply';
    } else if (name.endsWith('.splat')) {
      format = 'splat';
    } else if (name.endsWith('.spz')) {
      format = 'spz';
    } else if (name.endsWith('.rad')) {
      format = 'rad';
    } else {
      alert(t('unsupportedFormat'));
      return;
    }
    
    console.log('📦 Loading dropped model:', file.name, 'format:', format);
    
    // Create Blob URL and set as current model with format hint
    const blobUrl = URL.createObjectURL(file);
    setCurrentModel(file.name, blobUrl, format);
  }, [setCurrentModel, t]);

  const handleMainDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  // Task queue polling (must be called unconditionally before any early returns)
  useTaskQueue();

  // Boot screen
  if (isBooting) {
    return (
      <div className="boot-screen">
        <div className="boot-content">
          {bootError ? (
            <>
              <div className="boot-error-icon">⚠️</div>
              <h3>{t('errorOccurred')}</h3>
              <p className="boot-error-text">{bootError}</p>
            </>
          ) : (
            <>
              <div className="boot-spinner" />
              <h3>{t('loading')}</h3>
            </>
          )}
        </div>
      </div>
    );
  }

  if (!isAuthenticated && !isOwnerAccess) {
    return <AccessGate onUnlocked={loadPrivateData} />;
  }

  return (
    <div className="app-container">
      {/* Mobile menu button */}
      <button className="mobile-menu-btn" onClick={toggleSidebar}>
        <svg width="24" height="24" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
        </svg>
      </button>

      {/* Sidebar */}
      <Sidebar onUpload={handleUpload}>
        {activeView === 'photos' ? <PhotoAlbumList /> : <GalleryList />}
      </Sidebar>
      
      {/* Main content */}
      <main 
        className={`main-content ${!sidebarCollapsed ? 'sidebar-expanded' : ''}`}
        onDragOver={handleMainDragOver}
        onDrop={handleModelDrop}
      >
        {activeView === 'models' ? <ParticleBackground /> : null}
        
        {activeView === 'photos' ? <PhotoGalleryView /> : (
        <div className="viewer-container">
          {/* Empty state - shown when no model selected */}
          {!currentModelUrl && (
            <>
              <div className="empty-state">
                <svg className="empty-icon" fill="none" stroke="currentColor" strokeWidth="1.5" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M21 7.5l-9-5.25L3 7.5m18 0l-9 5.25m9-5.25v9l-9 5.25M3 7.5l9 5.25M3 7.5v9l9 5.25m0-9v9" />
                </svg>
                <h3>{t('emptyStateTitle')}</h3>
                <p>{t('emptyStateHint')}</p>
              </div>

              {/* PC Desktop Hint for drag & drop model generation */}
              {!sidebarCollapsed && (
                <div className="drag-to-sidebar-hint">
                  <svg className="hint-arrow" viewBox="0 0 60 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M 58 12 L 12 12" strokeDasharray="4 4" />
                    <path d="M 20 4 L 12 12 L 20 20" />
                  </svg>
                  <div className="hint-text">
                    {t('dragToSidebarHint')}
                  </div>
                </div>
              )}
            </>
          )}

          {/* Viewer with internal empty state handling */}
          <ViewerCanvas />
        </div>
        )}

        {/* Loading overlay */}
        {isLoading && (
          <div className="loading-overlay">
            <Loading 
              text={loadingText} 
              progress={loadingProgress} 
            />
          </div>
        )}
      </main>

      {/* Settings Modal */}
      <Settings />

      <AccessSetupPrompt
        open={showAccessSetupPrompt && isOwnerAccess && Boolean(authStatus?.setup_recommended)}
        onDismiss={dismissAccessSetupPrompt}
        onNeverRemind={suppressAccessSetupPrompt}
        onOpenSettings={openAccessSettings}
      />
      
      {/* Help Panel - always visible */}
      <Help />
      
      {/* Lightbox / Image Viewer */}
      <ImageViewer />
    </div>
  );
}

export default App;
