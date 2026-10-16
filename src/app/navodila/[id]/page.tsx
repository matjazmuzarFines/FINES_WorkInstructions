import { Suspense } from "react";
import { NavodiloPrikaz } from "@/components/navodila/NavodiloPrikaz";
import { Loading } from "@/components/ui/Notice";

export default function NavodiloStran() {
  return (
    <Suspense fallback={<Loading />}>
      <NavodiloPrikaz />
    </Suspense>
  );
}
