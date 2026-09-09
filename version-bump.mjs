import { readFileSync, writeFileSync } from "fs";

const targetVersion = process.env.npm_package_version;

// Preserve each file's own indentation and trailing-newline style instead of
// forcing JSON.stringify's defaults on it — the repo keeps manifest.json /
// manifest-beta.json on 2-space indent with a trailing newline while
// versions.json is tab-indented, and a bump that renormalises either look is
// a whole-file diff that has to be reverted by hand before a release MR is
// readable (#7bd39233).
function readJSON(path) {
  const raw = readFileSync(path, "utf8");
  const indentMatch = raw.match(/^\{\r?\n([ \t]+)/);
  return {
    data: JSON.parse(raw),
    indent: indentMatch ? indentMatch[1] : "\t",
    trailingNewline: raw.endsWith("\n"),
  };
}

function writeJSON(path, { data, indent, trailingNewline }) {
  const out = JSON.stringify(data, null, indent);
  writeFileSync(path, trailingNewline ? out + "\n" : out);
}

// manifest.json — bump to the target release version
const manifest = readJSON("manifest.json");
const { minAppVersion } = manifest.data;
manifest.data.version = targetVersion;
writeJSON("manifest.json", manifest);

// manifest-beta.json — what BRAT reads directly off the default branch for
// beta-channel installs. Nothing else keeps it in sync with manifest.json;
// left unbumped it rots silently (no CI signal short of manifest-check).
const manifestBeta = readJSON("manifest-beta.json");
manifestBeta.data.version = targetVersion;
writeJSON("manifest-beta.json", manifestBeta);

// versions.json — record targetVersion -> minAppVersion (read off manifest.json
// above, before the bump overwrote it in memory)
const versions = readJSON("versions.json");
versions.data[targetVersion] = minAppVersion;
writeJSON("versions.json", versions);
