"""
ЛР8 — COM-сервер планировщика РиПОД (comtypes, без typelib и без прав админа).

Сервер отдаёт наружу тот же планировщик, что и `ripod_app`: клиент передаёт
текст графа и параметры, а получает длины планов (makespan) и полные
текстовые отчёты по режимам.

Зачем нужен IDispatch «руками»
------------------------------
COM-класс описан без библиотеки типов (typelib), поэтому вместо vtable-
интерфейса сервер реализует OLE Automation: `IDispatch` с четырьмя
методами (`GetTypeInfoCount`, `GetTypeInfo`, `GetIDsOfNames`, `Invoke`).
Клиент работает через `comtypes.client.CreateObject(..., dynamic=True)` —
вызывает методы по имени, и comtypes сам находит DISPID и упаковывает
аргументы в `DISPPARAMS`. Имена реализации заданы в comtypes-стиле
(`IDispatch_GetIDsOfNames`, `IDispatch_Invoke`), чтобы перекрыть
реализацию по умолчанию из `comtypes.COMObject`.

Регистрация
-----------
Класс регистрируется в `HKCU\\Software\\Classes` (пользовательская ветка,
сливаемая в HKCR без прав администратора): запись в HKCR напрямую требует
повышения прав. В `LocalServer32` пишется командная строка запуска
`pythonw.exe lab8_planner_server.py`; COM при активации объекта сам
добавляет ключ `-Embedding`, по которому сервер поднимает фабрику классов
(`comtypes.server.localserver.run`).

------------------------------------------------------------------
ЗАПУСК
------------------------------------------------------------------
    python lab8_planner_server.py --register      # зарегистрировать COM-класс
    python lab8_client.py                         # запросы планов (см. ЛР8-клиент)
    python lab8_planner_server.py --unregister    # снять с регистрации
    python lab8_planner_server.py --serve         # поднять сервер вручную
------------------------------------------------------------------

Интерфейс (DISPID -> метод):
    1  SetGraph(text)      -> число операций (или -1 при ошибке)
    2  GetGraph()          -> текст графа
    3  SetProcessors(P)    -> применённое П (или -1)
    4  GetProcessors()     -> П
    5  SetTact(t)          -> применённый такт (или -1)
    6  GetTact()           -> такт
    7  SetPriority(rule)   -> правило приоритета (или "")
    8  GetModes()          -> список режимов через запятую
    9  GetPlan(mode)       -> длина плана (или -1)
   10  GetReport(mode)     -> полный текстовый отчёт
   11  GetVersion()        -> версия сервера
   12  GetLastError()      -> текст последней ошибки
"""

from __future__ import annotations

import os
import sys
import winreg
from typing import Any, Dict, List, Optional

import comtypes
import comtypes.automation as automation
from comtypes import CLSCTX_LOCAL_SERVER, COMObject, GUID
from comtypes.hresult import DISP_E_MEMBERNOTFOUND, E_FAIL, E_NOTIMPL, S_OK
from comtypes.server.localserver import run as run_localserver

import ripod_app as ripod


# ============================================================
# 1. Идентификация COM-класса
# ============================================================

CLSID = GUID("{C7A3E1B2-5D64-4F0A-9B21-8E7C3D5A6F42}")
PROGID = "Ripod.Planner.1"
PROGID_NOVERS = "Ripod.Planner"
DESC = "РиПОД: сервер планирования параллельных вычислений"
BASE_KEY = r"Software\Classes"

DISPID: Dict[str, int] = {
    "SetGraph": 1,
    "GetGraph": 2,
    "SetProcessors": 3,
    "GetProcessors": 4,
    "SetTact": 5,
    "GetTact": 6,
    "SetPriority": 7,
    "GetModes": 8,
    "GetPlan": 9,
    "GetReport": 10,
    "GetVersion": 11,
    "GetLastError": 12,
}


# ============================================================
# 2. Регистрация в HKCU\Software\Classes
# ============================================================

def server_command() -> str:
    """Командная строка локального сервера (COM допишет ключ -Embedding)."""
    exe = sys.executable
    if exe.lower().endswith("python.exe"):
        windowless = exe[: -len("python.exe")] + "pythonw.exe"
        if os.path.exists(windowless):
            exe = windowless
    exe = '"%s"' % exe if " " in exe else exe
    script = os.path.abspath(__file__)
    script = '"%s"' % script if " " in script else script
    return "%s %s" % (exe, script)


def _registry_entries() -> List[tuple]:
    """Пары (подключ, имя значения, значение) для регистрации класса."""
    clsid = str(CLSID)
    return [
        (r"CLSID\%s" % clsid, "", DESC),
        (r"CLSID\%s\ProgID" % clsid, "", PROGID),
        (r"CLSID\%s\VersionIndependentProgID" % clsid, "", PROGID_NOVERS),
        (r"CLSID\%s\LocalServer32" % clsid, "", server_command()),
        (PROGID, "", DESC),
        (r"%s\CLSID" % PROGID, "", clsid),
        (PROGID_NOVERS, "", DESC),
        (r"%s\CurVer" % PROGID_NOVERS, "", PROGID),
        (r"%s\CLSID" % PROGID_NOVERS, "", clsid),
    ]


def register() -> None:
    """Записать COM-класс в HKCU (права администратора не нужны)."""
    for subkey, name, value in _registry_entries():
        key = winreg.CreateKeyEx(
            winreg.HKEY_CURRENT_USER, "%s\\%s" % (BASE_KEY, subkey),
            0, winreg.KEY_WRITE,
        )
        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        key.Close()


def _delete_tree(root: int, path: str) -> None:
    """Удалить ключ реестра со всеми подключами."""
    try:
        key = winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    while True:
        try:
            sub = winreg.EnumKey(key, 0)
        except OSError:
            break
        winreg.CloseKey(key)
        _delete_tree(root, "%s\\%s" % (path, sub))
        key = winreg.OpenKey(root, path, 0, winreg.KEY_ALL_ACCESS)
    winreg.CloseKey(key)
    winreg.DeleteKey(root, path)


def unregister() -> None:
    """Удалить записи COM-класса из HKCU."""
    _delete_tree(winreg.HKEY_CURRENT_USER, "%s\\CLSID\\%s" % (BASE_KEY, CLSID))
    _delete_tree(winreg.HKEY_CURRENT_USER, "%s\\%s" % (BASE_KEY, PROGID))
    _delete_tree(winreg.HKEY_CURRENT_USER, "%s\\%s" % (BASE_KEY, PROGID_NOVERS))


# ============================================================
# 3. COM-объект планировщика
# ============================================================

_NAME_BY_DISPID: Dict[int, str] = {v: k for k, v in DISPID.items()}


class PlannerComponent(COMObject):
    """
    COM-объект: хранит текст графа и настройки, отдаёт планы по режимам.

    Члены интерфейса — обычные Python-методы; `IDispatch_Invoke` находит их
    по DISPID и вызывает с уже распакованными аргументами. Ошибки не
    превращаются в COM-исключения: метод возвращает -1 (или пустую строку),
    а текст причины остаётся в `GetLastError()`.
    """

    _com_interfaces_ = [automation.IDispatch]
    _reg_clsctx_ = CLSCTX_LOCAL_SERVER
    _reg_clsid_ = CLSID
    _reg_progid_ = PROGID
    _reg_novers_progid_ = PROGID_NOVERS
    _reg_desc_ = DESC
    _reg_class_spec_ = "lab8_planner_server.PlannerComponent"

    def __init__(self) -> None:
        super().__init__()
        self._graph_text = ripod.GRAPH_TEXT.strip()
        self._options = ripod.PlanOptions()
        self.last_error = ""

    # ---------- члены интерфейса ----------

    def SetGraph(self, text: Any) -> int:
        """Принять текст графа; вернуть число операций (-1 при ошибке)."""
        try:
            graph = ripod.parse_graph(str(text))
        except ValueError as exc:
            return self._fail(exc)
        if not graph.ops:
            return self._fail("Граф пуст: нет ни одной операции.")
        self._graph_text = str(text).strip()
        self.last_error = ""
        return len(graph.ops)

    def GetGraph(self) -> str:
        """Текст принятого графа."""
        return self._graph_text

    def SetProcessors(self, value: Any) -> int:
        """Задать число процессоров П; вернуть применённое значение."""
        try:
            processors = int(float(value))
        except (TypeError, ValueError):
            return self._fail("Число процессоров должно быть целым.")
        try:
            self._options = ripod.PlanOptions(
                processors=processors,
                priority=self._options.priority,
                tact=self._options.tact,
            )
        except ValueError as exc:
            return self._fail(exc)
        self.last_error = ""
        return self._options.processors

    def GetProcessors(self) -> int:
        """Текущее число процессоров."""
        return self._options.processors

    def SetTact(self, value: Any) -> float:
        """Задать время такта; вернуть применённое значение."""
        try:
            tact = float(value)
        except (TypeError, ValueError):
            return self._fail("Время такта должно быть числом.")
        try:
            self._options = ripod.PlanOptions(
                processors=self._options.processors,
                priority=self._options.priority,
                tact=tact,
            )
        except ValueError as exc:
            return self._fail(exc)
        self.last_error = ""
        return self._options.tact

    def GetTact(self) -> float:
        """Текущее время такта."""
        return self._options.tact

    def SetPriority(self, value: Any) -> str:
        """Задать правило приоритета списка; вернуть его же или ""."""
        rule = str(value).strip()
        if rule not in ripod.PRIORITIES:
            self._fail(
                "Неизвестное правило приоритета: %s. Допустимо: %s."
                % (rule, ", ".join(ripod.PRIORITIES))
            )
            return ""
        self._options = ripod.PlanOptions(
            processors=self._options.processors,
            priority=rule,
            tact=self._options.tact,
        )
        self.last_error = ""
        return rule

    def GetModes(self) -> str:
        """Список режимов планирования через запятую."""
        return ",".join(ripod.available_mode_keys())

    def GetPlan(self, mode: Any) -> int:
        """Длина плана режима (makespan) в тактах; -1 при ошибке."""
        try:
            spec = ripod.get_mode(str(mode))
            view = spec.build_view(
                ripod.parse_graph(self._graph_text), self._options,
            )
        except (KeyError, ValueError) as exc:
            return self._fail(exc)
        self.last_error = ""
        return view.makespan

    def GetReport(self, mode: Any) -> str:
        """Полный текстовый отчёт по режиму; "" при ошибке."""
        try:
            spec = ripod.get_mode(str(mode))
            view = spec.build_view(
                ripod.parse_graph(self._graph_text), self._options,
            )
        except (KeyError, ValueError) as exc:
            self._fail(exc)
            return ""
        self.last_error = ""
        return ripod.format_report(view, spec)

    def GetVersion(self) -> str:
        """Версия сервера."""
        return "РиПОД ЛР8: COM-сервер планировщика, версия 1.0"

    def GetLastError(self) -> str:
        """Текст последней ошибки (пусто, если ошибок не было)."""
        return self.last_error

    # ---------- служебное ----------

    def _fail(self, exc: Any) -> int:
        """Запомнить ошибку и вернуть признак неудачи."""
        self.last_error = str(exc)
        return -1

    def _dispatch(self, dispid: int, args: List[Any]) -> Any:
        """Вызвать член интерфейса по DISPID."""
        name = _NAME_BY_DISPID.get(dispid)
        if name is None:
            raise KeyError(dispid)
        return getattr(self, name)(*args)

    @staticmethod
    def _read_args(params: Any) -> List[Any]:
        """Аргументы из DISPPARAMS: там они лежат в обратном порядке."""
        if not params:
            return []
        packed = params[0]
        if not packed.rgvarg:
            return []
        args = [packed.rgvarg[i].value for i in range(packed.cArgs)]
        args.reverse()
        return args

    # ---------- IDispatch: OLE Automation без библиотеки типов ----------

    def IDispatch_GetTypeInfoCount(self) -> int:
        """Сведений о типах нет (typelib не используется)."""
        return 0

    def IDispatch_GetTypeInfo(self, this, itinfo, lcid, ptinfo):
        """Информация о типе не поддерживается."""
        if ptinfo:
            ptinfo[0] = None
        return E_NOTIMPL

    def IDispatch_GetIDsOfNames(self, this, riid, names, count, lcid, dispids):
        """Сопоставить имена членов интерфейса их DISPID."""
        for i in range(count):
            name = names[i]
            if name not in DISPID:
                return DISP_E_MEMBERNOTFOUND
            dispids[i] = DISPID[name]
        return S_OK

    def IDispatch_Invoke(self, this, dispid, riid, lcid, flags, params,
                         result, excepinfo, argerr):
        """
        Вызвать член интерфейса.

        Аргументы приходят в `DISPPARAMS` в обратном порядке; результат
        кладётся в `pVarResult`. Члены класса — только методы, поэтому на
        запрос свойства (DISPATCH_PROPERTYGET) отвечаем отказом: так
        динамический клиент comtypes переходит к вызову метода.
        """
        if flags == automation.DISPATCH_PROPERTYGET:
            return DISP_E_MEMBERNOTFOUND

        args = self._read_args(params)
        try:
            value = self._dispatch(dispid, args)
        except KeyError:
            return DISP_E_MEMBERNOTFOUND
        except TypeError as exc:
            self.last_error = "Неверные аргументы вызова: %s" % exc
            return E_FAIL

        if result:
            result[0].value = value
        return S_OK


# ============================================================
# 4. Точка входа: регистрация, сервер, справка
# ============================================================

USAGE = """РиПОД: COM-сервер планировщика (ЛР8)

    python lab8_planner_server.py --register      зарегистрировать COM-класс
    python lab8_planner_server.py --unregister    снять с регистрации
    python lab8_planner_server.py --serve         поднять сервер вручную

Клиент: python lab8_client.py [--graph FILE] [--proc P] [--tact T] [--mode M]"""


def main(argv: Optional[List[str]] = None) -> int:
    ripod.configure_stdout()
    tokens = {
        token.lower()
        for token in (sys.argv[1:] if argv is None else argv)
    }

    if tokens & {"--register", "/regserver", "-regserver"}:
        register()
        print("COM-класс зарегистрирован: %s = %s" % (PROGID, CLSID))
        return 0

    if tokens & {"--unregister", "/unregserver", "-unregserver"}:
        unregister()
        print("COM-класс снят с регистрации: %s" % PROGID)
        return 0

    if tokens & {"--serve", "/serve", "-embedding", "/embedding"}:
        # Этот путь использует сам COM: он запускает LocalServer32 с ключом
        # -Embedding и ждёт регистрации фабрики классов.
        run_localserver([PlannerComponent])
        return 0

    print(USAGE)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())


