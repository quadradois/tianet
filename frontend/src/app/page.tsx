import { FoundationShowcase } from "../components/foundation/foundation-showcase";

export default function Home() {
  return (
    <main className="mx-auto w-full max-w-(--size-content) px-5 py-12 sm:px-8 sm:py-16 lg:px-10 lg:py-20" id="conteudo-principal" tabIndex={-1}>
      <FoundationShowcase />
    </main>
  );
}
