"use client";
import { usePathname } from "next/navigation";
import Shell from "@/components/Shell";

export default function StaffLayout({ children }: { children: React.ReactNode }) {
  return usePathname() === "/staff/login" ? <>{children}</> : <Shell>{children}</Shell>;
}
