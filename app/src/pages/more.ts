import { h, ICON, svg } from "../ui";

const LINKS: [string, string, string, string][] = [
  ["musobaqa", "Strategiyalar musobaqasi", "9 ta strategiya virtual portfelda, SPUS bilan taqqoslab", ICON.trophy],
  ["jurnal", "Jurnalim", "Real savdolaringiz, R natijasi, intizom va tozalash", ICON.book],
  ["backtest", "Backtest", "Qoidalar tarixda tasodifdan yaxshiroqmi", ICON.flask],
  ["sozlamalar", "Sozlamalar", "Depozit, risk, mavzu, sinxron va zaxira", ICON.gear],
];

export default function (root: HTMLElement) {
  root.append(h("div", { class: "page" },
    h("header", { class: "page-head" }, h("h1", null, "Ko'proq")),
    h("nav", { class: "more" }, LINKS.map(([id, t, d, icon]) =>
      h("a", { class: "more-link", href: `#/${id}` }, svg(icon, 22), h("span", null, h("b", null, t), h("small", null, d)), svg(ICON.back, 18))))));
}
