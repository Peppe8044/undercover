import { useHash } from "./hooks";
import { Instructions } from "./Instructions";
import { Queue } from "./Queue";

function Page({ hash }: Readonly<{ hash: string }>) {
  if (hash === "#/instructions") return <Instructions />;
  return <Queue />;
}

export function App() {
  const hash = useHash();
  return (
    <>
      <header className="header">
        <a className="brand" href="#/">
          UnderCover <span className="tagline">Claims desk</span>
        </a>
        <nav aria-label="Main">
          <a
            href="#/"
            aria-current={hash === "#/instructions" ? undefined : "page"}
          >
            Queue
          </a>
          <a
            href="#/instructions"
            aria-current={hash === "#/instructions" ? "page" : undefined}
          >
            Instructions
          </a>
        </nav>
      </header>
      <main>
        <Page hash={hash} />
      </main>
    </>
  );
}
