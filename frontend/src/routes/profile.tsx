import { Navigate } from "@tanstack/react-router";
import { createFileRoute } from "@tanstack/react-router";

export const Route = createFileRoute("/profile")({
  component: ProfilePage,
});

function ProfilePage() {
  return <Navigate to="/settings" />;
}
