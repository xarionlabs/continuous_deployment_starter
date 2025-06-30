import type { ActionFunctionArgs } from "@remix-run/node";
import prisma from "../db.server";
import { withCors, withCorsLoader } from "../utils/cors.injector";

async function handleFollowUp({ request }: ActionFunctionArgs) {
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

    const { email, role, role_other, platforms, monthly_traffic, website_name } = body;

    if (!email || typeof email !== "string" || email.trim() === "") {
      return new Response(JSON.stringify({ error: "Valid email is required" }), { 
        status: 400, 
        headers: { "Content-Type": "application/json" } 
      });
    }

    const result = await prisma.followUpInfo.create({
      data: {
        email,
        role: role || null,
        role_other: role_other || null,
        platforms: platforms ? JSON.stringify(platforms) : null,
        monthly_traffic: monthly_traffic || null,
        website_name: website_name || null,
      },
    });

    return new Response(JSON.stringify({ data: result }), { 
      status: 201, 
      headers: { "Content-Type": "application/json" } 
    });
  } catch (error) {
    console.error("Error creating follow-up info:", error);
    return new Response(JSON.stringify({ error: "Internal server error" }), { 
      status: 500, 
      headers: { "Content-Type": "application/json" } 
    });
  }
}

export const action = withCors(handleFollowUp);
export const loader = withCorsLoader();