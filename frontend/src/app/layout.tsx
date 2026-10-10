import type { Metadata } from "next";
import { GeistMono } from "geist/font/mono";
import { GeistSans } from "geist/font/sans";
import { Toaster } from "sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import "./globals.css";

export const metadata: Metadata = {
  title: "QuarantineShock",
  description: "Notice in, rules out, shipments flagged. Decision support for pest quarantine changes.",
  icons: { icon: "/logo.svg" },
};

// Runs before paint so the saved theme never flashes. Dark is the default.
const themeScript = `try{var t=localStorage.getItem('qs-theme');document.documentElement.classList.toggle('dark',t!=='light')}catch(e){document.documentElement.classList.add('dark')}`;

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${GeistSans.variable} ${GeistMono.variable} dark h-full antialiased`} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeScript }} />
      </head>
      <body className="min-h-full">
        <TooltipProvider>{children}</TooltipProvider>
        <Toaster position="bottom-right" theme="system" richColors closeButton />
      </body>
    </html>
  );
}
