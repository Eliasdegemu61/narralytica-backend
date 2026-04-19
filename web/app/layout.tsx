import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Narralytica",
  description: "Signal dashboard preview for BTC and ETH decision engine runs.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
