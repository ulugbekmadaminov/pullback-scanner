// Mavzu ilova ochilishida darhol qo'llanadi (miltillashsiz)
try {
  var m = localStorage.getItem("saralash.mode") || "auto";
  if (m === "auto") m = matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  document.documentElement.dataset.mode = m;
} catch (e) { document.documentElement.dataset.mode = "light"; }
