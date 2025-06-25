import { json } from "@remix-run/node";
import type { LoaderFunctionArgs } from "@remix-run/node";
import prisma from "~/db.server";

export async function loader({ request }: LoaderFunctionArgs) {
  let dbStatus = "ok";
  let dbError = null;

  try {
    // Simple database connectivity check
    await prisma.$queryRaw`SELECT 1`;
  } catch (error) {
    dbStatus = "error";
    dbError = error instanceof Error ? error.message : "Unknown database error";
  }

  const healthData = {
    status: dbStatus === "ok" ? "ok" : "error",
    timestamp: new Date().toISOString(),
    uptime: process.uptime(),
    environment: process.env.SHOPIFY_CONFIG || "development",
    database: {
      status: dbStatus,
      error: dbError,
    },
  };

  return json(
    healthData,
    {
      status: dbStatus === "ok" ? 200 : 503,
      headers: {
        "Cache-Control": "no-cache",
      },
    }
  );
}