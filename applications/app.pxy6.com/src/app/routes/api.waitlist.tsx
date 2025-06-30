import type { ActionFunctionArgs } from "@remix-run/node";
import prisma from "../db.server";
import { withCors, withCorsLoader } from "../utils/cors.injector";

async function handleWaitlist({ request }: ActionFunctionArgs) {
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

    const { email, source } = body;

    if (!email || typeof email !== "string" || email.trim() === "") {
      return new Response(JSON.stringify({ error: "Valid email is required" }), { 
        status: 400, 
        headers: { "Content-Type": "application/json" } 
      });
    }

    const result = await prisma.waitingList.create({
      data: {
        email,
        source: source || null,
      },
    });

    return new Response(JSON.stringify({ data: result }), { 
      status: 201, 
      headers: { "Content-Type": "application/json" } 
    });
  } catch (error) {
    console.error("Error creating waitlist entry:", error);

    // Handle unique constraint violation
    if (error instanceof Error && error.message.includes("Unique constraint")) {
      return new Response(JSON.stringify({ error: "Email already exists in waitlist" }), { 
        status: 409, 
        headers: { "Content-Type": "application/json" } 
      });
    }

    return new Response(JSON.stringify({ error: "Internal server error" }), { 
      status: 500, 
      headers: { "Content-Type": "application/json" } 
    });
  }
}

export const action = withCors(handleWaitlist);
export const loader = withCorsLoader();