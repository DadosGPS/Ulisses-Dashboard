import { Suspense } from "react";
import { SeparadoresAcademia } from "@/components/academia/SeparadoresAcademia";

export default function AcademiaLayout({ children }: { children: React.ReactNode }) {
  return (
    <div>
      <Suspense>
        <SeparadoresAcademia />
      </Suspense>
      {children}
    </div>
  );
}
