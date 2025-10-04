# ─────────────────────────────────────────────────────────────────────────────
#  EcoStation CGR — Makefile narrado
# ─────────────────────────────────────────────────────────────────────────────
# ¿Qué estás construyendo?
#   Un ejecutable 'cgr' que calcula rutas en redes espaciales DTN usando
#   Contact Graph Routing (CGR) sobre un grafo de contactos (ventanas de
#   visibilidad). El objetivo es minimizar ETA (Earliest Time of Arrival).
#
# Algoritmo original (CGR, visión práctica):
#   - Modelo "store-carry-forward" de DTN: los nodos solo pueden enviar datos
#     cuando existe una ventana de contacto programada (contacto).
#   - Se construye un grafo temporal donde CADA CONTACTO es un vértice,
#     conectado con el siguiente si respeta la causalidad temporal.
#   - Se busca la ruta de mínima ETA (Dijkstra temporal), respetando ventanas,
#     latencia de propagación (OWLT) y caducidad del bundle.
#
# ¿Qué mejoras ya añade este repo (MVP+):
#   1) Poda por CAPACIDAD: si el bundle no cabe en la ventana (rate × duración),
#      descartamos el contacto. Simplificado como 'residual_bytes >= bundle_bytes'.
#   2) K rutas prácticas (--k N): tras hallar una ruta, CONSUMIMOS capacidad
#      (residual_bytes -= bundle_bytes) de los contactos usados y recomputamos.
#      Produce rutas alternativas realistas en constelaciones LEO con ISL.
#
# ¿Qué mejoras planeadas encajan aquí (siguientes pasos):
#   - Yen K-shortest (K rutas verdaderamente alternativas sin depender de consumo).
#   - Prioridades y expiración estricta (BPv7): preferencia por bundles urgentes.
#   - Capacidad dinámica por tiempo (consumo parcial, colas/backlog).
#   - "Bans" de contactos/transiciones para rutas edge/node-disjoint.
#
# Relación con la realidad de redes LEO:
#   - LEO-LEO tiene ventanas cortas y topología cambiante; CGR usa un "contact plan"
#     programado para prever qué enlaces existirán y cuándo.
#   - El consumo de capacidad aproxima congestión/uso de enlaces, tal y como pasa
#     cuando varias misiones comparten ISL o downlinks con estaciones.
#
# Targets útiles:
#   make            -> compila
#   make run        -> ejecuta un ejemplo sobre data/contacts.csv (k=3)
#   make debug      -> compila con símbolos de depuración
#   make clean      -> limpia objetos (.o)
#   make fclean     -> limpia todo (objetos + ejecutable)
#   make re         -> recompila desde cero (fclean + all)
#
# Estructura:
#   include/    : headers (APIs y structs)
#   src/        : implementación (heap, csv, cgr, main)
#   objetsLeo/  : archivos objeto (.o)
#   data/       : CSV de contactos de ejemplo
#   tests/      : script de prueba
# ─────────────────────────────────────────────────────────────────────────────

CC       := gcc
CFLAGS   := -O2 -Wall -Wextra -Wshadow -std=c17
DFLAGS   := -O0 -g3 -fsanitize=address,undefined -fno-omit-frame-pointer
INCLUDE  := -Iinclude

# ─── Directorios ──────────────────────────────────────────────────────────────
SRC_DIR  := src
OBJ_DIR  := objetsLeo

# ─── Detección automática de archivos fuente ─────────────────────────────────
SRC      := $(wildcard $(SRC_DIR)/*.c)
OBJ      := $(patsubst $(SRC_DIR)/%.c,$(OBJ_DIR)/%.o,$(SRC))
BIN      := cgr

# ─── Colores para output ──────────────────────────────────────────────────────
GREEN    := \033[32m
YELLOW   := \033[33m
BLUE     := \033[34m
RED      := \033[31m
RESET    := \033[0m

.PHONY: all clean fclean re run debug help

# ─── Target principal ─────────────────────────────────────────────────────────
all: $(BIN)
	@echo -e "$(GREEN)✓ Build completo:$(RESET) ./$(BIN)"

$(BIN): $(OBJ)
	@echo -e "$(BLUE)→ Linkeando$(RESET) $@"
	$(CC) $(CFLAGS) $(OBJ) -o $@

# ─── Compilación de objetos (con creación automática del directorio) ─────────
$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@echo -e "$(BLUE)→ Compilando$(RESET) $< → $@"
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@

# ─── Creación del directorio de objetos ──────────────────────────────────────
$(OBJ_DIR):
	@echo -e "$(YELLOW)→ Creando directorio$(RESET) $(OBJ_DIR)/"
	@mkdir -p $(OBJ_DIR)

# ─── Ejecución de prueba ──────────────────────────────────────────────────────
run: all
	@echo -e "$(YELLOW)Ejecutando demo (k=3) sobre data/contacts.csv$(RESET)"
	./$(BIN) --contacts data/contacts.csv --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3

# ─── Build con debug ──────────────────────────────────────────────────────────
debug: CFLAGS := $(DFLAGS)
debug: fclean $(BIN)
	@echo -e "$(GREEN)✓ Build debug listo$(RESET)"
	@echo -e "$(YELLOW)Sugerencia: ejecuta con ASan/UBSan en tu entorno$(RESET)"

# ─── Limpieza ─────────────────────────────────────────────────────────────────
clean:
	@echo -e "$(RED)→ Limpiando objetos$(RESET)"
	@rm -rf $(OBJ_DIR)

fclean: clean
	@echo -e "$(RED)→ Limpiando ejecutable$(RESET)"
	@rm -f $(BIN)

re: fclean all

# ─── Ayuda ────────────────────────────────────────────────────────────────────
help:
	@echo -e "$(BLUE)Targets disponibles:$(RESET)"
	@echo -e "  $(GREEN)make$(RESET)        -> compila el proyecto"
	@echo -e "  $(GREEN)make run$(RESET)    -> ejecuta ejemplo con k=3"
	@echo -e "  $(GREEN)make debug$(RESET)  -> compila con símbolos y sanitizers"
	@echo -e "  $(GREEN)make clean$(RESET)  -> elimina directorio objetsLeo/"
	@echo -e "  $(GREEN)make fclean$(RESET) -> elimina objetos y ejecutable"
	@echo -e "  $(GREEN)make re$(RESET)     -> recompila desde cero (fclean + all)"
	@echo -e "  $(GREEN)make help$(RESET)   -> muestra esta ayuda"

