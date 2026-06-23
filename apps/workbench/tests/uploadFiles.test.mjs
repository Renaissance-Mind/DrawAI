import assert from "node:assert/strict";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";
import test from "node:test";
import ts from "../node_modules/typescript/lib/typescript.js";

test("drop selection merges fallback files when dataTransfer items are incomplete", async () => {
  const { buildUploadConfirmation, selectedUploadFilesFromDrop } = await loadTsModule("../src/uploadFiles.ts");
  const files = [
    uploadFile("first.png", 101, 1001),
    uploadFile("second.png", 102, 1002),
    uploadFile("third.png", 103, 1003)
  ];
  const event = {
    dataTransfer: {
      items: [
        {
          kind: "file",
          getAsFile: () => files[0]
        }
      ],
      files
    }
  };

  const selected = await selectedUploadFilesFromDrop(event);
  const confirmation = await buildUploadConfirmation(selected);

  assert.deepEqual(selected.map((item) => item.file.name), ["first.png", "second.png", "third.png"]);
  assert.equal(confirmation.images.length, 3);
});

test("drop selection does not duplicate files when dataTransfer items are complete", async () => {
  const { selectedUploadFilesFromDrop } = await loadTsModule("../src/uploadFiles.ts");
  const files = [
    uploadFile("first.png", 101, 1001),
    uploadFile("second.png", 102, 1002),
    uploadFile("third.png", 103, 1003)
  ];
  const event = {
    dataTransfer: {
      items: files.map((file) => ({
        kind: "file",
        getAsFile: () => file
      })),
      files
    }
  };

  const selected = await selectedUploadFilesFromDrop(event);

  assert.deepEqual(selected.map((item) => item.file.name), ["first.png", "second.png", "third.png"]);
});

async function loadTsModule(relativePath) {
  const source = readFileSync(new URL(relativePath, import.meta.url), "utf8");
  const { outputText } = ts.transpileModule(source, {
    compilerOptions: {
      module: ts.ModuleKind.ES2022,
      target: ts.ScriptTarget.ES2020
    }
  });
  const dir = mkdtempSync(join(tmpdir(), "drawai-upload-files-"));
  const modulePath = join(dir, `${relativePath.split("/").at(-1).replace(/\.ts$/, "")}.mjs`);
  writeFileSync(modulePath, outputText);
  return import(pathToFileURL(modulePath).href);
}

function uploadFile(name, size, lastModified) {
  return {
    name,
    size,
    lastModified,
    type: "image/png"
  };
}
