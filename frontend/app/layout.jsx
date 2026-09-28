import "@fontsource-variable/inter";
import "@fontsource/barlow-condensed/700.css";
import "@fontsource/barlow-condensed/800-italic.css";
import "./globals.css";
import "./styles/timing.css";
import "./styles/motorsport.css";

export const metadata = {
  metadataBase: new URL("https://pitwall.shreybuilds.com"),
  title: {
    default: "PitWall | Formula 1 Analysis",
    template: "%s | PitWall",
  },
  description:
    "Formula 1 schedules, race classifications, session timing and reproducible rankings.",
  icons: {
    icon: "/icon.svg",
    shortcut: "/icon.svg",
    apple: "/icon.svg",
  },
  openGraph: {
    title: "PitWall | Formula 1 Analysis",
    description:
      "Published Formula 1 data with traceable rankings and explicit limitations.",
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
    title: "PitWall | Formula 1 Analysis",
    description:
      "Formula 1 schedules, classifications and transparent ranking evaluation.",
    images: ["/pitwall-og.svg"],
  },
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
