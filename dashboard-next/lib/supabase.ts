import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL!;
const key = process.env.NEXT_PUBLIC_SUPABASE_KEY!;
const schema = process.env.NEXT_PUBLIC_SUPABASE_SCHEMA ?? "fairnessops";

// Single client instance shared across the app.
export const supabase = createClient(url, key, {
  db: { schema },
  realtime: { params: { eventsPerSecond: 10 } },
});

export { schema };
