import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { getAdminStats, getAdminUsers, deleteAdminUser } from "@/lib/api";
import { ShieldCheck, Users, FileText, FolderGit2, Trash2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

interface AdminModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export function AdminModal({ isOpen, onClose }: AdminModalProps) {
  const [stats, setStats] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);

  const loadAdminData = async () => {
    setLoading(true);
    try {
      const [s, u] = await Promise.all([getAdminStats(), getAdminUsers()]);
      setStats(s);
      setUsers(u);
    } catch (err: any) {
      toast.error(err.message || "Failed to load admin management data.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      loadAdminData();
    }
  }, [isOpen]);

  const handleDeleteUser = async (userId: string, email: string) => {
    if (email.toLowerCase() === "kkssakthikumaran@gmail.com") {
      toast.error("Primary Administrator account cannot be deleted.");
      return;
    }
    if (!confirm(`Are you sure you want to delete user ${email} and all their data?`)) return;

    try {
      await deleteAdminUser(userId);
      toast.success(`User ${email} deleted successfully.`);
      loadAdminData();
    } catch (err: any) {
      toast.error(err.message || "Failed to delete user.");
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary/10 text-primary">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <DialogTitle className="font-serif-editorial text-xl">
                  PaperLens System Administrator Panel
                </DialogTitle>
                <DialogDescription className="text-xs text-muted-foreground">
                  Admin: <span className="font-semibold text-foreground">kkssakthikumaran@gmail.com</span>
                </DialogDescription>
              </div>
            </div>

            <Button
              variant="outline"
              size="sm"
              onClick={loadAdminData}
              disabled={loading}
              className="flex items-center gap-1.5 text-xs"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>
        </DialogHeader>

        {/* Metrics Grid */}
        <div className="grid grid-cols-3 gap-3 my-4">
          <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Users className="h-4 w-4" />
              <span className="text-xs font-medium">Registered Users</span>
            </div>
            <div className="mt-1 text-2xl font-bold font-serif-editorial text-foreground">
              {stats ? stats.total_users : "—"}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <FolderGit2 className="h-4 w-4" />
              <span className="text-xs font-medium">Workspaces</span>
            </div>
            <div className="mt-1 text-2xl font-bold font-serif-editorial text-foreground">
              {stats ? stats.total_workspaces : "—"}
            </div>
          </div>

          <div className="rounded-lg border border-border bg-card p-3 shadow-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <FileText className="h-4 w-4" />
              <span className="text-xs font-medium">Analyzed Papers</span>
            </div>
            <div className="mt-1 text-2xl font-bold font-serif-editorial text-foreground">
              {stats ? stats.total_papers : "—"}
            </div>
          </div>
        </div>

        {/* User Management Table */}
        <div className="space-y-2">
          <h3 className="text-sm font-semibold text-foreground">Registered Users & Accounts</h3>

          <div className="rounded-md border border-border overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="border-b border-border bg-muted/50 text-muted-foreground">
                <tr>
                  <th className="p-2.5 font-medium">User Name</th>
                  <th className="p-2.5 font-medium">Email</th>
                  <th className="p-2.5 font-medium">Provider</th>
                  <th className="p-2.5 font-medium">Role</th>
                  <th className="p-2.5 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-muted/30">
                    <td className="p-2.5 font-medium text-foreground">{u.name || "Scholar"}</td>
                    <td className="p-2.5 text-muted-foreground">{u.email}</td>
                    <td className="p-2.5 capitalize">{u.provider}</td>
                    <td className="p-2.5">
                      {u.is_admin ? (
                        <span className="rounded bg-primary/10 px-1.5 py-0.5 text-[10px] font-semibold text-primary">
                          Admin
                        </span>
                      ) : (
                        <span className="text-muted-foreground text-[11px]">Member</span>
                      )}
                    </td>
                    <td className="p-2.5 text-right">
                      {!u.is_admin && (
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteUser(u.id, u.email)}
                          className="h-7 w-7 text-destructive hover:bg-destructive/10"
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
