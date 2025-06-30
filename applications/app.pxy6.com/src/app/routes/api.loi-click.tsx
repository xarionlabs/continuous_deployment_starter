import type { ActionFunctionArgs } from "@remix-run/node";
import prisma from "../db.server";
import { withCors, withCorsLoader } from "../utils/cors.injector";

async function handleLoiClick({ request }: ActionFunctionArgs) {
  if (request.method !== "POST") {
    return new Response(JSON.stringify({ error: "Method not allowed" }), { 
      status: 405, 
      headers: { "Content-Type": "application/json" } 
    });
  }

  try {
    let body;
    try {
      body = await request.json();
    } catch {
      return new Response(JSON.stringify({ error: "Valid email is required" }), { 
        status: 400, 
        headers: { "Content-Type": "application/json" } 
      });
    }

    const { email } = body;

    if (!email || typeof email !== "string" || email.trim() === "") {
      return new Response(JSON.stringify({ error: "Valid email is required" }), { 
        status: 400, 
        headers: { "Content-Type": "application/json" } 
      });
    }

    const result = await prisma.loiClicks.create({
      data: {
        email: email.trim(),
      },
    });

    return new Response(JSON.stringify({ data: result }), { 
      status: 201, 
      headers: { "Content-Type": "application/json" } 
    });
  } catch (error) {
    console.error("Error tracking LOI click:", error);
    return new Response(JSON.stringify({ error: "Internal server error" }), { 
      status: 500, 
      headers: { "Content-Type": "application/json" } 
    });
  }
}

export const action = withCors(handleLoiClick);
export const loader = withCorsLoader();