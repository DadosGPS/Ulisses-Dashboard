import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";
import { Sidebar } from "@/components/layout/Sidebar";
import { cores } from "@/lib/theme";

export default async function AppLayout({ children }: { children: React.ReactNode }) {
  const supabase = await createClient();

  const {
    data: { user },
  } = await supabase.auth.getUser();

  if (!user) {
    redirect("/login");
  }

  const { data: perfil } = await supabase
    .from("profiles")
    .select("clube")
    .eq("id", user.id)
    .single();

  return (
    <div style={{ display: "flex", minHeight: "100vh", background: cores.bg }}>
      <Sidebar email={user.email ?? ""} clube={perfil?.clube} />
      <div style={{ flex: 1, minWidth: 0 }}>{children}</div>
    </div>
  );
}
