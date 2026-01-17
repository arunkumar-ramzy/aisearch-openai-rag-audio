import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { ArrowLeft, Loader2, Save } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";

interface Settings {
    rag_system_message: string;
    voice_assistant_system_message: string;
}

const defaultSettings: Settings = {
    rag_system_message: `You are a helpful assistant. Only answer questions based on information you searched in the knowledge base, accessible with the 'search' tool.
The user is listening to answers with audio, so it's *super* important that answers are as short as possible, a single sentence if at all possible.
Never read file names or source names or keys out loud.
Always use the following step-by-step instructions to respond:
1. Always use the 'search' tool to check the knowledge base before answering a question.
2. Always use the 'report_grounding' tool to report the source of information from the knowledge base.
3. Produce an answer that's as short as possible. If the answer isn't in the knowledge base, say you don't know.`,
    voice_assistant_system_message: `You are a helpful voice assistant.
The user is listening to answers with audio, so it's *super* important that answers are as short as possible, a single sentence if at all possible.
Provide helpful, friendly responses to the user's questions and requests.`
};

export default function SettingsPage() {
    const [settings, setSettings] = useState<Settings>(defaultSettings);
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [success, setSuccess] = useState(false);
    const navigate = useNavigate();

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const response = await fetch("/api/settings");
            if (response.ok) {
                const data = await response.json();
                setSettings(data);
            } else {
                console.error("Failed to load settings");
            }
        } catch (e) {
            console.error("Failed to load settings:", e);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSave = async () => {
        setIsSaving(true);
        setError(null);
        setSuccess(false);

        try {
            const response = await fetch("/api/settings", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(settings),
            });

            if (response.ok) {
                setSuccess(true);
                setTimeout(() => setSuccess(false), 3000);
            } else {
                const data = await response.json();
                setError(data.error || "Failed to save settings");
            }
        } catch (e) {
            setError("Failed to save settings");
            console.error("Failed to save settings:", e);
        } finally {
            setIsSaving(false);
        }
    };

    const handleBack = () => {
        navigate("/");
    };

    if (isLoading) {
        return (
            <div className="flex min-h-screen items-center justify-center bg-gray-100">
                <Loader2 className="h-8 w-8 animate-spin text-purple-600" />
            </div>
        );
    }

    return (
        <div className="min-h-screen bg-gray-100 p-4 md:p-8">
            <div className="mx-auto max-w-4xl">
                {/* Header */}
                <div className="mb-6 flex items-center gap-4">
                    <Button
                        variant="ghost"
                        size="icon"
                        onClick={handleBack}
                        className="shrink-0"
                    >
                        <ArrowLeft className="h-5 w-5" />
                    </Button>
                    <h1 className="text-2xl font-bold text-gray-900 md:text-3xl">
                        System Instructions
                    </h1>
                </div>

                {/* Error/Success Messages */}
                {error && (
                    <div className="mb-4 rounded-md bg-red-50 p-4 text-red-800">
                        {error}
                    </div>
                )}
                {success && (
                    <div className="mb-4 rounded-md bg-green-50 p-4 text-green-800">
                        Settings saved successfully!
                    </div>
                )}

                {/* Settings Form */}
                <div className="space-y-6">
                    {/* Voice Assistant Instructions */}
                    <div className="rounded-lg bg-white p-6 shadow-sm">
                        <Label htmlFor="voice-assistant" className="mb-2 block text-base font-semibold">
                            Voice Assistant Mode Instructions
                        </Label>
                        <p className="mb-3 text-sm text-gray-600">
                            These instructions are used when Azure Search is not configured (voice assistant mode).
                        </p>
                        <Textarea
                            id="voice-assistant"
                            value={settings.voice_assistant_system_message}
                            onChange={e =>
                                setSettings({ ...settings, voice_assistant_system_message: e.target.value })
                            }
                            rows={8}
                            className="w-full font-mono text-sm"
                        />
                    </div>

                    {/* RAG Instructions */}
                    <div className="rounded-lg bg-white p-6 shadow-sm">
                        <Label htmlFor="rag-mode" className="mb-2 block text-base font-semibold">
                            RAG Mode Instructions
                        </Label>
                        <p className="mb-3 text-sm text-gray-600">
                            These instructions are used when Azure Search is configured (RAG mode).
                        </p>
                        <Textarea
                            id="rag-mode"
                            value={settings.rag_system_message}
                            onChange={e => setSettings({ ...settings, rag_system_message: e.target.value })}
                            rows={10}
                            className="w-full font-mono text-sm"
                        />
                    </div>

                    {/* Action Buttons */}
                    <div className="flex justify-end gap-3">
                        <Button variant="outline" onClick={handleBack}>
                            Cancel
                        </Button>
                        <Button onClick={handleSave} disabled={isSaving} className="min-w-[100px]">
                            {isSaving ? (
                                <>
                                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                    Saving...
                                </>
                            ) : (
                                <>
                                    <Save className="mr-2 h-4 w-4" />
                                    Save
                                </>
                            )}
                        </Button>
                    </div>
                </div>
            </div>
        </div>
    );
}
