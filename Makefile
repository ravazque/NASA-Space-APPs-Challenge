
CC       := cc
CFLAGS   := -O2 -Wall -Wextra -Werror -Wshadow -std=c17
DFLAGS   := -O0 -g3 -fsanitize=address,undefined -fno-omit-frame-pointer
INCLUDE  := -Iinclude
LDLIBS   := -lm -lcurl

SRC_DIR  := src
OBJ_DIR  := objetsLeo

CORE_SRCS := cgr.c csv.c heap.c leo_metrics.c nasa_api.c
CORE_OBJS := $(patsubst %.c,$(OBJ_DIR)/%.o,$(CORE_SRCS))
API_MAIN  := $(OBJ_DIR)/api_main.o
BIN       := cgr_api

GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
RED    := \033[31m
RESET  := \033[0m

.PHONY: all clean fclean re run debug help

all: $(BIN)
	@echo -e "$(GREEN)✓ Build completo:$(RESET) ./$(BIN)"

$(BIN): $(CORE_OBJS) $(API_MAIN)
	@echo -e "$(BLUE)→ Linkeando$(RESET) $@"
	$(CC) $(CFLAGS) $(CORE_OBJS) $(API_MAIN) -o $@ $(LDLIBS)

$(OBJ_DIR):
	@mkdir -p $(OBJ_DIR)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@echo -e "$(BLUE)→ Compilando$(RESET) $< → $@"
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@

run: all
	@echo -e "$(YELLOW)Ejemplo (API SODA)$(RESET)"
	./$(BIN) --dataset abcd-1234 --app-token TU_TOKEN --src 100 --dst 200 --t0 0 --bytes 5e7 --k 3 --cycles 1

debug: CFLAGS := $(DFLAGS)
debug: fclean all
	@echo -e "$(GREEN)✓ Build debug listo$(RESET)"

clean:
	@echo -e "$(RED)→ Limpiando objetos$(RESET)"
	@rm -rf $(OBJ_DIR)

fclean: clean
	@echo -e "$(RED)→ Limpiando ejecutables$(RESET)"
	@rm -f $(BIN)

re: fclean all

help:
	@echo "Targets: make | run | debug | clean | fclean | re"
