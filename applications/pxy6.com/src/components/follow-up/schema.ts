import { z } from "zod";

// Schema for role and platform validation
export const formSchema = z.object({
  role: z.enum(["founder", "ecommerce", "marketing", "growth", "other"]),
  roleOther: z.string().optional(),
  websiteName: z.string().min(1, "Please enter your website name"),
  platforms: z.array(z.string()).min(1, "Please select at least one platform"),
  monthlyTraffic: z.enum([
    "<50k", 
    "50k-100k", 
    "100k-250k", 
    "250k-500k", 
    "500k-1M", 
    ">1M"
  ]),
}).refine((data) => {
  if (data.role === "other" && (!data.roleOther || data.roleOther.trim() === "")) {
    return false;
  }
  return true;
}, {
  message: "Please specify your role",
  path: ["roleOther"]
});

export type FormValues = z.infer<typeof formSchema>;

// Role options
export const roleOptions = [
  { value: "founder", label: "Founder / Owner", icon: "User" },
  { value: "ecommerce", label: "Head of E-commerce", icon: "Store" },
  { value: "marketing", label: "Head of Marketing", icon: "ChartBar" },
  { value: "growth", label: "Growth / Performance Marketer", icon: "ChartBar" },
  { value: "other", label: "Other", icon: "Briefcase" },
];

// Platform options
export const platformOptions = [
  { id: "shopify", label: "Shopify" },
  { id: "magento", label: "Magento" },
  { id: "woocommerce", label: "WooCommerce" },
  { id: "custom", label: "Custom" },
  { id: "none", label: "Not running a store (yet)" },
];

// Traffic options
export const trafficOptions = [
  { value: "<50k", label: "< 50k visits" },
  { value: "50k-100k", label: "50k - 100k visits" },
  { value: "100k-250k", label: "100k - 250k visits" },
  { value: "250k-500k", label: "250k - 500k visits" },
  { value: "500k-1M", label: "500k - 1M visits" },
  { value: ">1M", label: "> 1M visits" },
];
