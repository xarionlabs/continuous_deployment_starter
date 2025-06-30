
import { insertFollowUpInfo, insertLoiClick } from "@/services/databaseService";
import { FormValues } from "@/components/follow-up/schema";

export const submitFollowUpInfo = async (email: string, data: FormValues) => {
  // Prepare role data
  const roleData = data.role === "other" ? data.roleOther : undefined;
  
  // Log what we're trying to insert for debugging
  console.log("Attempting to insert into follow_up_info:", {
    email,
    role: data.role,
    role_other: roleData,
    platforms: data.platforms,
    monthly_traffic: data.monthlyTraffic,
    website_name: data.websiteName
  });
  
  // Insert information into the follow_up_info table
  const { error, data: responseData } = await insertFollowUpInfo({
    email: email,
    role: data.role,
    role_other: roleData,
    platforms: data.platforms,
    monthly_traffic: data.monthlyTraffic,
    website_name: data.websiteName
  });
  
  if (error) {
    console.error("Error submitting follow-up data:", error);
  } else {
    console.log("Follow-up data submitted successfully:", responseData);
  }
  
  return { error, data: responseData };
};

export const trackLOIClick = async (email: string) => {
  if (!email || typeof email !== 'string' || email.trim() === '') {
    console.error("Invalid email for LOI tracking:", email);
    return { error: new Error("Invalid email"), data: null };
  }
  
  console.log("Tracking LOI click for email:", email);
  
  try {
    const { error, data } = await insertLoiClick(email.trim());
    
    if (error) {
      console.error("Error tracking LOI click:", error);
      return { error, data: null };
    } else {
      console.log("LOI click tracked successfully:", data);
      return { error: null, data };
    }
  } catch (exception) {
    console.error("Exception during LOI click tracking:", exception);
    return { error: exception, data: null };
  }
};
