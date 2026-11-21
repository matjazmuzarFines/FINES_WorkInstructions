import { createReadStream, promises as fs } from "node:fs";
import path from "node:path";
import { Readable } from "node:stream";
import { preveriAdmina, razlogIzklopa, varnaPot } from "@/lib/treningStreznik";

const TIPI: Record<string, string> = {
  ".mp4": "video/mp4",
  ".webm": "video/webm",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".gif": "image/gif",
  ".svg": "image/svg+xml",
  ".json": "application/json; charset=utf-8",
  ".md": "text/plain; charset=utf-8",
  ".txt": "text/plain; charset=utf-8",
  ".log": "text/plain; charset=utf-8",
  ".csv": "text/plain; charset=utf-8",
  ".py": "text/plain; charset=utf-8",
};

/**
 * GET ?pot=modeli/<model>/<ai>/<poskus>/<datoteka>&t=<žeton>
 * Vrne izhodno datoteko poskusa. Podpira Range (premikanje po videu).
 * Vhodnih CAD datotek ne vrača - te ostanejo samo na disku.
 */
export async function GET(req: Request) {
  const izklop = razlogIzklopa();
  if (izklop) return new Response(izklop, { status: 403 });
  const ni = await preveriAdmina(req);
  if (ni) return new Response(ni, { status: 401 });

  const pot = new URL(req.url).searchParams.get("pot") ?? "";
  if (!/^modeli\/[^/]+\/(astra|fable)\/[^/]+\/.+/.test(pot)) return new Response("Neveljavna pot.", { status: 400 });
  const abs = varnaPot(pot);
  if (!abs) return new Response("Neveljavna pot.", { status: 400 });

  let st;
  try {
    st = await fs.stat(abs);
  } catch {
    return new Response("Datoteka ne obstaja.", { status: 404 });
  }
  if (!st.isFile()) return new Response("Ni datoteka.", { status: 400 });

  const tip = TIPI[path.extname(abs).toLowerCase()] ?? "application/octet-stream";
  const glave: Record<string, string> = {
    "Content-Type": tip,
    "Accept-Ranges": "bytes",
    "Cache-Control": "no-store",
    "X-Content-Type-Options": "nosniff",
  };
  if (tip === "application/octet-stream") {
    glave["Content-Disposition"] = `attachment; filename="${path.basename(abs).replace(/[^\w.-]/g, "_")}"`;
  }

  const range = /^bytes=(\d*)-(\d*)$/.exec(req.headers.get("range") ?? "");
  if (range && (range[1] || range[2]) && st.size > 0) {
    let zacetek = range[1] ? Number(range[1]) : NaN;
    let konec = range[2] ? Number(range[2]) : st.size - 1;
    if (Number.isNaN(zacetek)) {
      zacetek = Math.max(0, st.size - konec);
      konec = st.size - 1;
    }
    konec = Math.min(konec, st.size - 1);
    if (zacetek > konec) {
      return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${st.size}` } });
    }
    const tok = Readable.toWeb(createReadStream(abs, { start: zacetek, end: konec })) as ReadableStream;
    return new Response(tok, {
      status: 206,
      headers: { ...glave, "Content-Range": `bytes ${zacetek}-${konec}/${st.size}`, "Content-Length": String(konec - zacetek + 1) },
    });
  }

  const tok = Readable.toWeb(createReadStream(abs)) as ReadableStream;
  return new Response(tok, { headers: { ...glave, "Content-Length": String(st.size) } });
}
