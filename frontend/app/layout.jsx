import "./globals.css";

export const metadata = {
  title: "PitWall | F1 Predictions",
  description: "Clean sprint and race prediction dashboard powered by GitHub Actions data.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning>{children}</body>
    </html>
  );
}
