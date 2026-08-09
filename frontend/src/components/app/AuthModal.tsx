import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { oauthLogin, registerUser } from "@/lib/api";
import { ShieldCheck, Mail, User as UserIcon, Lock } from "lucide-react";
import { toast } from "sonner";

const API_BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api/v1";

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: (user: any) => void;
}

type View = "main" | "oauth-google" | "oauth-microsoft";

export function AuthModal({ isOpen, onClose, onSuccess }: AuthModalProps) {
  const [mode, setMode] = useState<"register" | "login">("register");
  const [view, setView] = useState<View>("main");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [oauthEmail, setOauthEmail] = useState("");
  const [oauthName, setOauthName] = useState("");
  const [loading, setLoading] = useState(false);

  const resetAndClose = () => {
    setView("main");
    setOauthEmail("");
    setOauthName("");
    onClose();
  };

  const handleEmailAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please enter both email and password.");
      return;
    }
    setLoading(true);
    try {
      if (mode === "register") {
        const res = await registerUser(email, password, name || undefined);
        localStorage.setItem("paperlens_access_token", res.access_token ?? "");
        toast.success("Account created successfully!");
        onSuccess(res.user);
      } else {
        const resp = await fetch(`${API_BASE}/auth/login`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (!resp.ok) throw new Error("Invalid credentials");
        const data = await resp.json();
        localStorage.setItem("paperlens_access_token", data.access_token);
        toast.success("Logged in successfully!");
        onSuccess(data.user);
      }
      resetAndClose();
    } catch (err: any) {
      toast.error(err.message || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleOAuthSubmit = async (provider: "google" | "microsoft") => {
    if (!oauthEmail) {
      toast.error("Please enter your email address.");
      return;
    }
    setLoading(true);
    try {
      const displayName = oauthName || (provider === "google" ? "Google User" : "Microsoft User");
      const res = await oauthLogin(provider, oauthEmail, displayName, `${provider}_sub_${Date.now()}`);
      localStorage.setItem("paperlens_access_token", res.access_token ?? "");
      toast.success(`Signed in with ${provider === "google" ? "Google" : "Microsoft"}!`);
      onSuccess(res.user);
      resetAndClose();
    } catch (err: any) {
      toast.error(err.message || "OAuth authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  const googleIcon = (
    <svg className="h-4 w-4" viewBox="0 0 24 24">
      <path fill="#4285F4" d="M23.745 12.27c0-.7-.06-1.4-.19-2.07H12v4.51h6.6c-.29 1.52-1.14 2.82-2.4 3.68v3.05h3.88c2.27-2.09 3.665-5.17 3.665-9.17z" />
      <path fill="#34A853" d="M12 24c3.24 0 5.95-1.08 7.93-2.91l-3.88-3.05c-1.08.72-2.45 1.16-4.05 1.16-3.12 0-5.77-2.1-6.72-4.93H1.27v3.15C3.25 21.3 7.31 24 12 24z" />
      <path fill="#FBBC05" d="M5.28 14.27c-.25-.72-.38-1.49-.38-2.27s.13-1.55.38-2.27V6.58H1.27C.46 8.2 0 10.04 0 12s.46 3.8 1.27 5.42l4.01-3.15z" />
      <path fill="#EA4335" d="M12 4.75c1.77 0 3.35.61 4.6 1.8l3.42-3.42C17.95 1.19 15.24 0 12 0 7.31 0 3.25 2.7 1.27 6.58l4.01 3.15c.95-2.83 3.6-4.98 6.72-4.98z" />
    </svg>
  );

  const msIcon = (
    <svg className="h-4 w-4" viewBox="0 0 23 23">
      <path fill="#f35325" d="M1 1h10v10H1z" />
      <path fill="#81bc06" d="M12 1h10v10H12z" />
      <path fill="#05a6f0" d="M1 12h10v10H1z" />
      <path fill="#ffba08" d="M12 12h10v10H12z" />
    </svg>
  );

  // OAuth sub-view
  if (view === "oauth-google" || view === "oauth-microsoft") {
    const provider = view === "oauth-google" ? "google" : "microsoft";
    const providerLabel = provider === "google" ? "Google" : "Microsoft";
    return (
      <Dialog open={isOpen} onOpenChange={(open) => !open && resetAndClose()}>
        <DialogContent className="sm:max-w-sm">
          <DialogHeader>
            <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10">
              {provider === "google" ? googleIcon : msIcon}
            </div>
            <DialogTitle className="text-center text-xl">
              Continue with {providerLabel}
            </DialogTitle>
            <DialogDescription className="text-center text-xs text-muted-foreground">
              Enter the email linked to your {providerLabel} account.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-3 py-2">
            <div>
              <Label className="text-xs">Full Name (optional)</Label>
              <div className="relative mt-1">
                <UserIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="text"
                  placeholder="Sakthi Kumaran"
                  value={oauthName}
                  onChange={(e) => setOauthName(e.target.value)}
                  className="pl-8 text-xs"
                />
              </div>
            </div>
            <div>
              <Label className="text-xs">{providerLabel} Email Address</Label>
              <div className="relative mt-1">
                <Mail className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="email"
                  required
                  autoFocus
                  placeholder={provider === "google" ? "you@gmail.com" : "you@outlook.com"}
                  value={oauthEmail}
                  onChange={(e) => setOauthEmail(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && handleOAuthSubmit(provider)}
                  className="pl-8 text-xs"
                />
              </div>
            </div>

            <Button
              onClick={() => handleOAuthSubmit(provider)}
              disabled={loading}
              className="w-full text-xs font-semibold"
            >
              {loading ? "Signing in..." : `Continue with ${providerLabel}`}
            </Button>

            <button
              type="button"
              onClick={() => setView("main")}
              className="w-full text-center text-xs text-muted-foreground hover:text-foreground"
            >
              Back to sign in options
            </button>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  // Main auth view
  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && resetAndClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-full bg-primary/10 text-primary">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <DialogTitle className="text-center text-2xl">
            {mode === "register" ? "Create PaperLens Account" : "Welcome Back"}
          </DialogTitle>
          <DialogDescription className="text-center text-xs text-muted-foreground">
            Sign in or register to analyze research papers and access admin controls.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-2">
          <div className="grid grid-cols-2 gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={loading}
              onClick={() => { setView("oauth-google"); setOauthEmail(""); setOauthName(""); }}
              className="flex items-center justify-center gap-2 border-border py-2 text-xs font-medium"
            >
              {googleIcon}
              Google
            </Button>

            <Button
              variant="outline"
              type="button"
              disabled={loading}
              onClick={() => { setView("oauth-microsoft"); setOauthEmail(""); setOauthName(""); }}
              className="flex items-center justify-center gap-2 border-border py-2 text-xs font-medium"
            >
              {msIcon}
              Microsoft
            </Button>
          </div>

          <div className="relative my-3 text-center text-xs">
            <span className="bg-background px-2 text-muted-foreground">Or continue with Email</span>
            <div className="absolute inset-x-0 top-1/2 -z-10 border-t border-border" />
          </div>

          <form onSubmit={handleEmailAuth} className="space-y-3">
            {mode === "register" && (
              <div>
                <Label className="text-xs">Full Name</Label>
                <div className="relative mt-1">
                  <UserIcon className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                  <Input
                    type="text"
                    placeholder="Sakthi Kumaran"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="pl-8 text-xs"
                  />
                </div>
              </div>
            )}

            <div>
              <Label className="text-xs">Email Address</Label>
              <div className="relative mt-1">
                <Mail className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="email"
                  required
                  placeholder="kkssakthikumaran@gmail.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="pl-8 text-xs"
                />
              </div>
            </div>

            <div>
              <Label className="text-xs">Password</Label>
              <div className="relative mt-1">
                <Lock className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="password"
                  required
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="pl-8 text-xs"
                />
              </div>
            </div>

            <Button type="submit" disabled={loading} className="w-full text-xs font-semibold">
              {loading ? "Processing..." : mode === "register" ? "Create Account" : "Sign In"}
            </Button>
          </form>
        </div>

        <div className="mt-2 text-center text-xs text-muted-foreground">
          {mode === "register" ? (
            <>
              Already have an account?{" "}
              <button
                type="button"
                onClick={() => setMode("login")}
                className="font-medium text-primary hover:underline"
              >
                Sign In
              </button>
            </>
          ) : (
            <>
              Need a new account?{" "}
              <button
                type="button"
                onClick={() => setMode("register")}
                className="font-medium text-primary hover:underline"
              >
                Register
              </button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
