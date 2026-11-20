import { redirect } from "next/navigation";

/** Os limiares de velocidade passaram a ser um separador da Carga externa. */
export default function VelocidadePage() {
  redirect("/carga-externa/velocidade");
}
