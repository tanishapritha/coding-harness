import "./globals.css";

export const metadata = {
  title: "Forge — AI coding workspace",
  description: "A reliable coding-agent workspace for real repositories.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="en"><body>{children}</body></html>;
}
