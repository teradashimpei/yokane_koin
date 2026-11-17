import "./globals.css";

export const metadata = { title: "よかね 話し手用" };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="ja"><body>{children}</body></html>;
}
