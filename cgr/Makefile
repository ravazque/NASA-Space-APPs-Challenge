CC       := cc
CFLAGS   := -O2 -Wall -Wextra -Werror -Wshadow -std=c17
DFLAGS   := -O0 -g3 -fsanitize=address,undefined -fno-omit-frame-pointer
INCLUDE  := -Iinclude
LDLIBS   := -lm -lcurl

SRC_DIR  := src
OBJ_DIR  := build

CORE_SRCS := cgr.c csv.c heap.c leo_metrics.c nasa_api.c
CORE_OBJS := $(patsubst %.c,$(OBJ_DIR)/%.o,$(CORE_SRCS))
LIVE_MAIN := $(OBJ_DIR)/cgr_live.o
BIN       := cgr_live

GREEN  := \033[32m
YELLOW := \033[33m
BLUE   := \033[34m
RED    := \033[31m
RESET  := \033[0m

.PHONY: all clean fclean re run debug help

all: $(BIN)
	@echo -e "$(GREEN)✓ Build complete:$(RESET) ./$(BIN)"

$(BIN): $(CORE_OBJS) $(LIVE_MAIN)
	@echo -e "$(BLUE)→ Linking$(RESET) $@"
	$(CC) $(CFLAGS) $(CORE_OBJS) $(LIVE_MAIN) -o $@ $(LDLIBS)

$(OBJ_DIR):
	@mkdir -p $(OBJ_DIR)

$(OBJ_DIR)/%.o: $(SRC_DIR)/%.c | $(OBJ_DIR)
	@echo -e "$(BLUE)→ Compiling$(RESET) $< → $@"
	$(CC) $(CFLAGS) $(INCLUDE) -c $< -o $@

run: all
	@echo -e "$(YELLOW)═══════════════════════════════════════════════════════$(RESET)"
	@echo -e "$(GREEN)  CGR Real-Time Demo with Synthetic Satellite Network$(RESET)"
	@echo -e "$(YELLOW)═══════════════════════════════════════════════════════$(RESET)"
	@echo ""
	./$(BIN) --source synth --synth-n 12 --tick 15 --k 5 --bytes 50000000 --src 100 --dst 200

debug: CFLAGS := $(DFLAGS)
debug: fclean all
	@echo -e "$(GREEN)✓ Debug build ready$(RESET)"

clean:
	@echo -e "$(RED)→ Cleaning objects$(RESET)"
	@rm -rf $(OBJ_DIR)

fclean: clean
	@echo -e "$(RED)→ Cleaning executables$(RESET)"
	@rm -f $(BIN)

re: fclean all

help:
	@echo "Targets: make | run | debug | clean | fclean | re"
	@echo ""
	@echo "Run modes:"
	@echo "  make run              - Real-time synthetic satellite network"
	@echo "  ./cgr_live --help     - See all options"
	