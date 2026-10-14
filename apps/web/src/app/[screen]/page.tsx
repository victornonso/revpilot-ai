import { Suspense } from "react";
import { notFound } from "next/navigation";
import Workspace from "@/components/Workspace";
const screens = [
  "overview",
  "pipeline",
  "forecasting",
  "customers",
  "analyst",
  "automations",
  "recovery",
  "reports",
  "operations",
];
export async function generateMetadata({
  params,
}: {
  params: Promise<{ screen: string }>;
}) {
  const { screen } = await params;
  return { title: screen[0].toUpperCase() + screen.slice(1) };
}
export default async function Page({
  params,
}: {
  params: Promise<{ screen: string }>;
}) {
  const { screen } = await params;
  if (!screens.includes(screen)) notFound();
  return (
    <Suspense fallback={<div className="boot">Connecting to RevPilot…</div>}>
      <Workspace screen={screen} />
    </Suspense>
  );
}
