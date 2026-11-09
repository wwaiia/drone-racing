import type { Metadata } from "next";
import { Inter, Oswald } from "next/font/google";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "cyrillic"], variable: "--font-inter" });
const oswald = Oswald({
  subsets: ["latin", "cyrillic"],
  weight: ["500", "600", "700"],
  variable: "--font-oswald",
});

export const metadata: Metadata = {
  title: "Дрон Рейсинг — мероприятия",
  description:
    "Ближайшие соревнования по дрон-рейсингу в России: региональные гонки по областям и всероссийские старты. Даты, места, призовой фонд, регистрация.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ru">
      <body className={`${inter.variable} ${oswald.variable} antialiased`}>{children}</body>
    </html>
  );
}
