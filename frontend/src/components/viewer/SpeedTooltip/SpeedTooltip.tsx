import React from 'react';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '@/store';
import styles from './SpeedTooltip.module.css';

export type SpeedMode = 'fast' | 'precision' | null;

interface SpeedTooltipProps {
    mode: SpeedMode;
}

export const SpeedTooltip: React.FC<SpeedTooltipProps> = ({ mode }) => {
    const { t } = useTranslation();
    const sidebarCollapsed = useAppStore(state => state.sidebarCollapsed);
    
    const displayMode = mode ?? 'fast';
    const content = displayMode === 'fast' 
        ? `⚡ ${t('fastMode')}`
        : `🔍 ${t('precisionMode')}`;
    
    return (
        <div className={`${styles.tooltip} ${mode ? styles.visible : ''} ${!sidebarCollapsed ? styles.sidebarExpanded : ''}`}>
            {content}
        </div>
    );
};
