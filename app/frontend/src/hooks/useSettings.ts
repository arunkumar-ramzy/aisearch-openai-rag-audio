import { useState, useEffect } from "react";

const SETTINGS_KEY = "voicerag_settings";
const DEFAULT_VOICE = "alloy";

export type Settings = {
    voice: string;
};

const DEFAULT_SETTINGS: Settings = {
    voice: DEFAULT_VOICE,
};

function loadSettings(): Settings {
    try {
        const stored = localStorage.getItem(SETTINGS_KEY);
        if (stored) {
            return { ...DEFAULT_SETTINGS, ...JSON.parse(stored) };
        }
    } catch (error) {
        console.error("Failed to load settings:", error);
    }
    return DEFAULT_SETTINGS;
}

function saveSettings(settings: Settings): void {
    try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch (error) {
        console.error("Failed to save settings:", error);
    }
}

export function useSettings() {
    const [settings, setSettings] = useState<Settings>(loadSettings);
    const [isLoaded, setIsLoaded] = useState(false);

    useEffect(() => {
        setSettings(loadSettings());
        setIsLoaded(true);
    }, []);

    const updateSettings = (updates: Partial<Settings>) => {
        const newSettings = { ...settings, ...updates };
        setSettings(newSettings);
        saveSettings(newSettings);
    };

    return {
        settings,
        updateSettings,
        isLoaded,
    };
}
