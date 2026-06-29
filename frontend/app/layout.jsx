import "./globals.css";

export const metadata = {
  metadataBase: new URL("https://pitwall.shreybuilds.com"),
  title: {
    default: "PitWall | F1 Prediction Intelligence",
    template: "%s | PitWall",
  },
  description: "Source-aware Formula 1 prediction intelligence with full-grid rankings, model status, and transparent fallback states.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
  openGraph: {
    title: "PitWall | F1 Prediction Intelligence",
    description: "Full-grid F1 prediction boards, source health, model status, and race strategy signals generated from trusted project contracts.",
    url: "https://pitwall.shreybuilds.com",
    siteName: "PitWall",
    images: [
      {
        url: "/pitwall-og.svg",
        width: 1200,
        height: 630,
        alt: "PitWall race intelligence dashboard visual",
      },
    ],
    type: "website",
  },
  twitter: {
    card: "summary_large_image",
    title: "PitWall | F1 Prediction Intelligence",
    description: "Source-aware F1 prediction intelligence with full-grid rankings and transparent source health.",
    images: ["/pitwall-og.svg"],
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
