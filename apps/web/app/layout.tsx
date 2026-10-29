import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Paper2Proof | Development workspace",
  description: "Source-linked experimental verification, under development.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body>{children}</body></html>;
}
