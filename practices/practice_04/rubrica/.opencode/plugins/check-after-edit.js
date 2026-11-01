/**
 * Hook check-after-edit.
 *
 * После каждой правки кода сам запускает единственный доверенный runner проекта
 * scripts/check.sh и возвращает его вывод в результат инструмента. Агент видит
 * FAIL или PASS рядом со своим диффом — отдельный вызов в чат не нужен.
 *
 * Важно: hook ничего не чинит и не блокирует инструмент. Он только сообщает.
 * Решение по правке остаётся за агентом и за человеком.
 */

// Имена инструментов, которыми агент меняет файлы. Список полный намеренно:
// в opencode 1.18.30 правка в основном идёт через apply_patch, и хук,
// который слушает только edit/write, молча пропускает половину правок.
const EDIT_TOOLS = new Set(["edit", "write", "patch", "apply_patch", "multiedit"])

// Пути, за которыми следим: код проекта и его проверки.
const WATCHED = [/\/src\/rubrica\//, /\/tests\//, /\/mcp\/rubrica_mcp\//]
const RUNNER = "scripts/check.sh"

function isWatched(filePath) {
  if (typeof filePath !== "string" || filePath.length === 0) return false
  if (filePath.includes("/.venv/")) return false
  if (filePath.includes("/__pycache__/")) return false
  // apply_patch передаёт пути относительными («tests/test_core.py»), а edit и write —
  // абсолютными. Нормализуем к виду «/tests/…», иначе относительный путь не подходит под фильтр.
  const normalized = filePath.startsWith("/") ? filePath : `/${filePath.replace(/^\.\//, "")}`
  return WATCHED.some((pattern) => pattern.test(normalized))
}

/**
 * apply_patch не передаёт путь отдельным аргументом, а кладёт его в patchText.
 * Достаточно взять все абсолютные пути из патча и проверить их по очереди.
 */
function touchedFiles(input) {
  const direct = input.args?.filePath ?? input.args?.path
  if (typeof direct === "string" && direct.length > 0) return [direct]

  const patchText = input.args?.patchText ?? input.args?.patch
  if (typeof patchText === "string") {
    const matches = patchText.match(/[^\s*]+\.(?:py|json|yaml|yml)/g) ?? []
    return [...new Set(matches.filter((candidate) => candidate.includes("/")))]
  }
  return []
}

export const CheckAfterEdit = async ({ $ }) => {
  return {
    "tool.execute.after": async (input, output) => {
      if (!EDIT_TOOLS.has(input.tool)) return

      const files = touchedFiles(input)
      if (files.length === 0) return
      const watched = files.filter(isWatched)
      if (watched.length === 0) return

      const cwd = process.cwd()
      let result
      try {
        result = await $`sh ${RUNNER}`.cwd(cwd).quiet().nothrow()
      } catch (error) {
        output.output = [
          output.output,
          "",
          `── check-after-edit: не удалось запустить ${RUNNER} в ${cwd}: ${String(error)}`,
          "Проверь, что ты в корне проекта rubrica и что scripts/check.sh исполняем.",
        ].join("\n")
        return
      }

      const code = result.exitCode ?? 0
      // unittest пишет и в stdout, и в stderr. Берём оба потока: иначе в отчёт
      // попадёт только «compileall: ok» и агент не увидит, какой тест упал.
      const stdout = (result.stdout ?? "").toString().trim()
      const stderr = (result.stderr ?? "").toString().trim()
      const combined = [stdout, stderr].filter(Boolean).join("\n")
      const tail = combined.split("\n").slice(-16).join("\n")

      output.output = [
        output.output,
        "",
        `── check-after-edit: ${code === 0 ? "PASS" : `FAIL (exit ${code})`} · ${RUNNER} после ${input.tool}: ${watched.join(", ")}`,
        tail,
        code === 0
          ? "Проверка зелёная, можно продолжать."
          : "Проверка красная. Runner под зелёный результат не трогаем (docs/style-guide.md, правило 4) — чинится код.",
      ].join("\n")

      output.metadata = {
        ...output.metadata,
        checkAfterEdit: { exitCode: code, runner: RUNNER, files: watched },
      }
    },
  }
}