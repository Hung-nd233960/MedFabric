import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Send, Eye, Zap, CheckCircle2, XCircle, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { telegramApi } from "@/lib/api";

export default function NotificationsPage() {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [chatId, setChatId] = useState<string | null>(null);
  const [previewText, setPreviewText] = useState<string | null>(null);
  const [loading, setLoading] = useState<"test" | "preview" | "report" | null>(null);

  useEffect(() => {
    telegramApi.status()
      .then(r => { setConfigured(r.data.configured); setChatId(r.data.chat_id); })
      .catch(() => setConfigured(false));
  }, []);

  const handleTest = async () => {
    setLoading("test");
    try {
      await telegramApi.sendTest();
      toast.success("Test message sent to Telegram.");
    } catch {
      toast.error("Failed to send test message.");
    } finally {
      setLoading(null);
    }
  };

  const handlePreview = async () => {
    setLoading("preview");
    try {
      const r = await telegramApi.previewReport();
      setPreviewText(r.data.text);
    } catch {
      toast.error("Failed to generate report preview.");
    } finally {
      setLoading(null);
    }
  };

  const handleSendReport = async () => {
    setLoading("report");
    try {
      await telegramApi.sendReport();
      toast.success("12h report sent to Telegram.");
    } catch {
      toast.error("Failed to send report.");
    } finally {
      setLoading(null);
    }
  };

  return (
    <div className="p-6 max-w-lg space-y-4">
      <h1 className="text-xl font-semibold">Notifications</h1>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Telegram</CardTitle>
          <CardDescription>
            Send login alerts and 12-hour submission reports to a Telegram chat.
            Configured via <code className="text-xs bg-muted px-1 py-0.5 rounded">TELEGRAM_BOT_TOKEN</code> and{" "}
            <code className="text-xs bg-muted px-1 py-0.5 rounded">TELEGRAM_CHAT_ID</code> env vars.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Status */}
          <div className="flex items-center gap-2 text-sm">
            {configured === null ? (
              <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
            ) : configured ? (
              <>
                <CheckCircle2 className="h-4 w-4 text-green-500" />
                <span>Configured — chat ID ending in <span className="font-mono">{chatId}</span></span>
              </>
            ) : (
              <>
                <XCircle className="h-4 w-4 text-destructive" />
                <span className="text-muted-foreground">Not configured — set env vars to enable.</span>
              </>
            )}
          </div>

          {/* Actions — only shown when configured */}
          {configured && (
            <div className="space-y-2">
              <Button
                variant="outline"
                className="w-full gap-2"
                onClick={handleTest}
                disabled={!!loading}
              >
                {loading === "test" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Zap className="h-4 w-4" />}
                Send test message
              </Button>

              <Button
                variant="outline"
                className="w-full gap-2"
                onClick={handlePreview}
                disabled={!!loading}
              >
                {loading === "preview" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Eye className="h-4 w-4" />}
                Preview 12h report
              </Button>

              <Button
                className="w-full gap-2"
                onClick={handleSendReport}
                disabled={!!loading}
              >
                {loading === "report" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Send 12h report now
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Report preview */}
      {previewText && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Report preview</CardTitle>
            <CardDescription>This is what the next scheduled report will look like.</CardDescription>
          </CardHeader>
          <CardContent>
            <pre className="text-xs bg-muted rounded-md p-3 whitespace-pre-wrap leading-relaxed font-mono">
              {previewText}
            </pre>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
