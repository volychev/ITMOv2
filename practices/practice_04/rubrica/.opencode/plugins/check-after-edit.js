/**
 * Hook check-after-edit.
 *
 * После каждой правки в src/ или tests/ сам запускает единственный доверенный
 * runner проекта scripts/check.sh и возвращает его вывод в результат
 * инструмента. Агент видит FAIL или PASS в том же сообщении, где он увидел
 * свой diff, — не нужно отдельного вызова в чат.
 *
 * Важно: hook ничего не чинит и не блокирует инструмент. Он только сообщает.
 * Решение по правке остаётся за агентом и за человеком.
 */

const WATCHED = [/\/src\/rubrica\//, /\/tests\//, /\/mcp\/rubrica_mcp\//]
const RUNNER = "scripts/check.sh"
const TIMEOUT_MS = 120000

function isWatched(filePath) {
  if (typeof filePath !== "string") return false
  if (filePath.includes("/.venv/")) return false
  if (filePath.includes("/__pycache__/")) return false
  return WATCHED.some((pattern) => pattern.test(filePath))
}

export const CheckAfterEdit = async ({ $ }) => {
  return {
    "tool.execute.after": async (input, output) => {
      if (input.tool !== "edit" && input.tool !== "write" && input.tool !== "patch") return

      const filePath = input.args?.filePath ?? input.args?.path
      if (!isWatched(filePath)) return

      try {
        const result = await $`sh ${RUNNER}`.cwd(process.cwd()).quiet().nothrow()
        const code = result.exitCode ?? 0
        const stdout = (result.stdout ?? "").toString().trim()
        const stderr = (result.stderr ?? "").toString().trim()

        const verdict = code === 0 ? "PASS" : `FAIL (exit ${code})`
        const tail = (stdout || stderr).split("\n").slice(-12).join("\n")

        output.output = [
          output.output,
          "",
          `── check-after-edit: ${verdict} · ran ${RUNNER} after ${input.tool} ${filePath}`,
          tail,
          code === 0
            ? "Проверка зелёная, можно продолжать."
            : "Проверка красная. Не правишь runner под зелёный результат — чини код (docs/style-guide.md, правило 4).",
        ]
          .filter((line) => line !== undefined)
          .join("\n")

        output.metadata = {
          ...output.metadata,
          checkAfterEdit: { exitCode: code, runner: RUNNER, file: filePath },
        }
      } catch (error) {
        output.output = [
          output.output,
          "",
          `── check-after-edit: не удалось запустить ${RUNNER}: ${String(error)}`,
        ].join("\n")
      }
    },
  }
}