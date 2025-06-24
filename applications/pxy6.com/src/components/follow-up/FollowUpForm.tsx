import React from "react";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { 
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Checkbox } from "@/components/ui/checkbox";
import { Button } from "@/components/ui/button";
import { Briefcase, User, Store, ChartBar } from "lucide-react";
import { formSchema, FormValues, roleOptions, platformOptions, trafficOptions } from "./schema";

interface FollowUpFormProps {
  onSubmit: (data: FormValues) => Promise<void>;
  isSubmitting: boolean;
}

const FollowUpForm: React.FC<FollowUpFormProps> = ({ onSubmit, isSubmitting }) => {
  const form = useForm<FormValues>({
    resolver: zodResolver(formSchema),
    defaultValues: {
      role: undefined,
      roleOther: "",
      websiteName: "",
      platforms: [],
      monthlyTraffic: undefined,
    },
  });
  
  const watchRole = form.watch("role");

  // Add form state logging
  console.log('Form state:', {
    values: form.getValues(),
    errors: form.formState.errors,
    isSubmitting: form.formState.isSubmitting
  });
  
  // Map icon strings to actual components
  const getIconComponent = (iconName: string) => {
    switch (iconName) {
      case 'User': return <User className="mr-2 h-4 w-4" />;
      case 'Store': return <Store className="mr-2 h-4 w-4" />;
      case 'ChartBar': return <ChartBar className="mr-2 h-4 w-4" />;
      case 'Briefcase': 
      default: return <Briefcase className="mr-2 h-4 w-4" />;
    }
  };

  return (
    <Form {...form}>
      <form 
        onSubmit={(e) => {
          console.log('Form submit event triggered');
          form.handleSubmit((data) => {
            console.log('Form validation passed, submitting data:', data);
            return onSubmit(data);
          })(e);
        }} 
        className="space-y-6"
      >
        {/* Website name field */}
        <FormField
          control={form.control}
          name="websiteName"
          render={({ field }) => (
            <FormItem>
              <FormLabel>What's your website name?</FormLabel>
              <FormControl>
                <Input placeholder="e.g. mystore.com" {...field} />
              </FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        
        {/* Role selection */}
        <FormField
          control={form.control}
          name="role"
          render={({ field }) => (
            <FormItem className="space-y-3">
              <FormLabel>What best describes your role?</FormLabel>
              <RadioGroup
                onValueChange={field.onChange}
                defaultValue={field.value}
                className="space-y-1"
              >
                {roleOptions.map((role) => (
                  <FormItem key={role.value} className="flex items-center space-x-3 space-y-0">
                    <FormControl>
                      <RadioGroupItem value={role.value} />
                    </FormControl>
                    <FormLabel className="flex items-center font-normal">
                      {getIconComponent(role.icon)}
                      {role.label}
                    </FormLabel>
                  </FormItem>
                ))}
              </RadioGroup>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Conditional field for "Other" role */}
        {watchRole === "other" && (
          <FormField
            control={form.control}
            name="roleOther"
            render={({ field }) => (
              <FormItem>
                <FormLabel>Please specify your role</FormLabel>
                <FormControl>
                  <Input placeholder="Your role" {...field} />
                </FormControl>
                <FormMessage />
              </FormItem>
            )}
          />
        )}

        {/* Platform checkboxes */}
        <FormField
          control={form.control}
          name="platforms"
          render={() => (
            <FormItem>
              <FormLabel>What platform does your store run on?</FormLabel>
              <div className="space-y-2">
                {platformOptions.map((platform) => (
                  <FormField
                    key={platform.id}
                    control={form.control}
                    name="platforms"
                    render={({ field }) => {
                      return (
                        <FormItem
                          key={platform.id}
                          className="flex flex-row items-start space-x-3 space-y-0"
                        >
                          <FormControl>
                            <Checkbox
                              checked={field.value?.includes(platform.id)}
                              onCheckedChange={(checked) => {
                                return checked
                                  ? field.onChange([...field.value, platform.id])
                                  : field.onChange(
                                      field.value?.filter(
                                        (value) => value !== platform.id
                                      )
                                    )
                              }}
                            />
                          </FormControl>
                          <FormLabel className="font-normal">
                            {platform.label}
                          </FormLabel>
                        </FormItem>
                      )
                    }}
                  />
                ))}
              </div>
              <FormMessage />
            </FormItem>
          )}
        />

        {/* Monthly traffic */}
        <FormField
          control={form.control}
          name="monthlyTraffic"
          render={({ field }) => (
            <FormItem className="space-y-3">
              <FormLabel>Roughly how much traffic do you get per month?</FormLabel>
              <RadioGroup
                onValueChange={field.onChange}
                defaultValue={field.value}
                className="space-y-1"
              >
                {trafficOptions.map((option) => (
                  <FormItem key={option.value} className="flex items-center space-x-3 space-y-0">
                    <FormControl>
                      <RadioGroupItem value={option.value} />
                    </FormControl>
                    <FormLabel className="font-normal">
                      {option.label}
                    </FormLabel>
                  </FormItem>
                ))}
              </RadioGroup>
              <FormMessage />
            </FormItem>
          )}
        />
        
        <Button type="submit" className="w-full" disabled={isSubmitting}>
          {isSubmitting ? "Submitting..." : "Submit Information"}
        </Button>
      </form>
    </Form>
  );
};

export default FollowUpForm;
