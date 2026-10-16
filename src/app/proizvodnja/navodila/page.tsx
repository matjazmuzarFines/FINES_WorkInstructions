import { Suspense } from "react";
import { NavodilaPregled } from "@/components/navodila/NavodilaPregled";
import { Loading } from "@/components/ui/Notice";

export default function NavodilaStran() {
  return (
    <Suspense fallback={<Loading />}>
      <NavodilaPregled />
    </Suspense>
  );
}
