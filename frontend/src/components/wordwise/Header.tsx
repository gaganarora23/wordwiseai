import { Link } from "@tanstack/react-router";

export function Header({ right }: { right?: React.ReactNode }) {
  return (
    <header className="border-b-2 border-foreground bg-card">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-3">
        <Link to="/" className="flex items-center gap-2 font-display text-2xl font-bold">
          <span className="grid h-9 w-9 place-items-center rounded-md border-2 border-foreground bg-secondary shadow-block-sm">W</span>
          WordWise
        </Link>
        {right}
      </div>
    </header>
  );
}
