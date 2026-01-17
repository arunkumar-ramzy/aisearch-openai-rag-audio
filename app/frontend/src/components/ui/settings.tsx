import { useState } from "react";
import { useTranslation } from "react-i18next";
import { X, Save } from "lucide-react";

import { Button } from "./button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./card";

type VoiceOption = {
    id: string;
    name: string;
    description: string;
};

const VOICE_OPTIONS: VoiceOption[] = [
    { id: "alloy", name: "Alloy", description: "Neutral, balanced voice" },
    { id: "echo", name: "Echo", description: "Male, calm voice" },
    { id: "shimmer", name: "Shimmer", description: "Female, expressive voice" },
];

type Properties = {
    isOpen: boolean;
    currentVoice: string;
    isConversationActive: boolean;
    onSave: (voice: string) => void;
    onClose: () => void;
};

export function Settings({ isOpen, currentVoice, isConversationActive, onSave, onClose }: Properties) {
    const [selectedVoice, setSelectedVoice] = useState(currentVoice);
    const { t } = useTranslation();

    if (!isOpen) return null;

    const handleSave = () => {
        onSave(selectedVoice);
        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
            <Card className="m-4 max-w-md w-full">
                <CardHeader>
                    <div className="flex items-center justify-between">
                        <CardTitle className="text-xl">{t("settings.title")}</CardTitle>
                        <Button
                            variant="ghost"
                            size="icon"
                            onClick={onClose}
                            className="h-8 w-8"
                        >
                            <X className="h-4 w-4" />
                        </Button>
                    </div>
                    <CardDescription>{t("settings.description")}</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                    {isConversationActive && (
                        <div className="rounded-lg bg-yellow-50 p-3 text-sm text-yellow-800">
                            {t("settings.conversationActiveWarning")}
                        </div>
                    )}

                    <div className="space-y-2">
                        <label className="text-sm font-medium">{t("settings.voiceLabel")}</label>
                        <div className="space-y-2">
                            {VOICE_OPTIONS.map((voice) => (
                                <button
                                    key={voice.id}
                                    onClick={() => !isConversationActive && setSelectedVoice(voice.id)}
                                    disabled={isConversationActive}
                                    className={`w-full rounded-lg border p-3 text-left transition-colors ${
                                        selectedVoice === voice.id
                                            ? "border-purple-500 bg-purple-50"
                                            : "border-gray-200 bg-white hover:bg-gray-50"
                                    } ${isConversationActive ? "cursor-not-allowed opacity-50" : "cursor-pointer"}`}
                                >
                                    <div className="font-medium">{voice.name}</div>
                                    <div className="text-sm text-gray-500">{voice.description}</div>
                                </button>
                            ))}
                        </div>
                    </div>

                    <div className="flex justify-end gap-2">
                        <Button
                            variant="outline"
                            onClick={onClose}
                        >
                            {t("settings.cancel")}
                        </Button>
                        <Button
                            onClick={handleSave}
                            disabled={isConversationActive}
                            className="bg-purple-500 hover:bg-purple-600"
                        >
                            <Save className="mr-2 h-4 w-4" />
                            {t("settings.save")}
                        </Button>
                    </div>
                </CardContent>
            </Card>
        </div>
    );
}
