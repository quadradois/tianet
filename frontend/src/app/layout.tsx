import type { Metadata, Viewport } from "next";
import type { ReactNode } from "react";

import "./globals.css";

export const metadata: Metadata = {
  title: "Frontend MVP",
  description: "Fundação visual governada do Frontend MVP.",
};

export const viewport: Viewport = {
  colorScheme: "light dark",
  themeColor: [
    { color: "#f7f8fa", media: "(prefers-color-scheme: light)" },
    { color: "#17191d", media: "(prefers-color-scheme: dark)" },
  ],
};

type RootLayoutProps = Readonly<{
  children: ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html data-scroll-behavior="smooth" lang="pt-BR">
      <body>
        <a className="skip-link" href="#conteudo-principal">Pular para o conteudo</a>
        {children}
      </body>
    </html>
  );
}
