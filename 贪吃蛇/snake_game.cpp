/*
 * Snake Game - Complete Implementation
 * Written in C for Windows Environment
 * Features: Multiple maps, score tracking, step counting, full English UI
 */

#include <stdio.h>
#include <stdlib.h>
#include <conio.h>
#include <windows.h>
#include <time.h>

/* ==================== CONSTANTS ==================== */
#define MAX_WIDTH 40
#define MAX_HEIGHT 25
#define MAX_SNAKE_LENGTH 800
#define MAX_FOOD_COUNT 10
#define MAX_MAPS 3

/* Game speed (milliseconds) */
#define SPEED_EASY 150
#define SPEED_MEDIUM 100
#define SPEED_HARD 70

/* Console colors */
#define COLOR_DEFAULT 7
#define COLOR_WALL 12      /* Red */
#define COLOR_SNAKE_HEAD 10 /* Green */
#define COLOR_SNAKE_BODY 2  /* Dark Green */
#define COLOR_FOOD 14      /* Yellow */
#define COLOR_EMPTY 0      /* Black */
#define COLOR_TEXT 15      /* White */

/* Map symbols */
#define SYMBOL_WALL '#'
#define SYMBOL_EMPTY ' '
#define SYMBOL_SNAKE_HEAD 'O'
#define SYMBOL_SNAKE_BODY 'o'
#define SYMBOL_FOOD '*'

/* ==================== DATA STRUCTURES ==================== */
typedef struct {
    int x;
    int y;
} Position;

typedef struct {
    Position body[MAX_SNAKE_LENGTH];
    int length;
    int direction; /* 0=Up, 1=Right, 2=Down, 3=Left */
    int nextDirection;
} Snake;

typedef struct {
    Position pos;
    int active;
    int value;
} Food;

typedef struct {
    char name[50];
    int width;
    int height;
    char grid[MAX_HEIGHT][MAX_WIDTH];
    int foodCount;
    int speed;
    char description[200];
} Map;

/* ==================== GLOBAL VARIABLES ==================== */
Map maps[MAX_MAPS];
int currentMap = 0;
Snake snake;
Food foods[MAX_FOOD_COUNT];
int score = 0;
int steps = 0;
int gameRunning = 0;
int gamePaused = 0;
int totalFoodEaten = 0;
int totalFoodOnMap = 0;

/* ==================== CONSOLE FUNCTIONS ==================== */
void setCursorPosition(int x, int y) {
    COORD coord;
    coord.X = x;
    coord.Y = y;
    SetConsoleCursorPosition(GetStdHandle(STD_OUTPUT_HANDLE), coord);
}

void setConsoleColor(int color) {
    SetConsoleTextAttribute(GetStdHandle(STD_OUTPUT_HANDLE), color);
}

void hideCursor() {
    CONSOLE_CURSOR_INFO cursorInfo;
    cursorInfo.bVisible = FALSE;
    cursorInfo.dwSize = 1;
    SetConsoleCursorInfo(GetStdHandle(STD_OUTPUT_HANDLE), &cursorInfo);
}

void clearScreen() {
    system("cls");
}

/* ==================== MAP DEFINITIONS ==================== */
void initializeMaps() {
    int i, j;

    /* Map 1: Classic Box (Easy) */
    strcpy(maps[0].name, "Classic Box");
    strcpy(maps[0].description, "Standard rectangular arena. Perfect for beginners.");
    maps[0].width = 20;
    maps[0].height = 15;
    maps[0].foodCount = 5;
    maps[0].speed = SPEED_EASY;

    for (i = 0; i < maps[0].height; i++) {
        for (j = 0; j < maps[0].width; j++) {
            if (i == 0 || i == maps[0].height - 1 || j == 0 || j == maps[0].width - 1)
                maps[0].grid[i][j] = SYMBOL_WALL;
            else
                maps[0].grid[i][j] = SYMBOL_EMPTY;
        }
    }

    /* Map 2: Cross Maze (Medium) */
    strcpy(maps[1].name, "Cross Maze");
    strcpy(maps[1].description, "Cross-shaped obstacles in the center. Medium difficulty.");
    maps[1].width = 30;
    maps[1].height = 20;
    maps[1].foodCount = 7;
    maps[1].speed = SPEED_MEDIUM;

    for (i = 0; i < maps[1].height; i++) {
        for (j = 0; j < maps[1].width; j++) {
            if (i == 0 || i == maps[1].height - 1 || j == 0 || j == maps[1].width - 1)
                maps[1].grid[i][j] = SYMBOL_WALL;
            else if ((i >= 7 && i <= 12 && j == 10) || (i >= 7 && i <= 12 && j == 19))
                maps[1].grid[i][j] = SYMBOL_WALL;
            else if ((i == 7 || i == 12) && j >= 10 && j <= 19)
                maps[1].grid[i][j] = SYMBOL_WALL;
            else
                maps[1].grid[i][j] = SYMBOL_EMPTY;
        }
    }

    /* Map 3: Spiral Dungeon (Hard) */
    strcpy(maps[2].name, "Spiral Dungeon");
    strcpy(maps[2].description, "Complex spiral walls. Only for experts!");
    maps[2].width = 35;
    maps[2].height = 22;
    maps[2].foodCount = 10;
    maps[2].speed = SPEED_HARD;

    for (i = 0; i < maps[2].height; i++) {
        for (j = 0; j < maps[2].width; j++) {
            if (i == 0 || i == maps[2].height - 1 || j == 0 || j == maps[2].width - 1)
                maps[2].grid[i][j] = SYMBOL_WALL;
            else if (i == 5 && j >= 5 && j <= 29)
                maps[2].grid[i][j] = SYMBOL_WALL;
            else if (i == 16 && j >= 5 && j <= 29)
                maps[2].grid[i][j] = SYMBOL_WALL;
            else if (j == 5 && i >= 5 && i <= 16)
                maps[2].grid[i][j] = SYMBOL_WALL;
            else if (j == 29 && i >= 5 && i <= 16)
                maps[2].grid[i][j] = SYMBOL_WALL;
            else if (i == 10 && j >= 10 && j <= 24)
                maps[2].grid[i][j] = SYMBOL_WALL;
            else if (j == 17 && i >= 10 && i <= 13)
                maps[2].grid[i][j] = SYMBOL_WALL;
            else
                maps[2].grid[i][j] = SYMBOL_EMPTY;
        }
    }
}

/* ==================== DRAWING FUNCTIONS ==================== */
void drawBorder(int x, int y, int width, int height) {
    int i;
    setConsoleColor(COLOR_WALL);
    setCursorPosition(x, y);
    printf("+");
    for (i = 0; i < width; i++) printf("-");
    printf("+");

    for (i = 0; i < height; i++) {
        setCursorPosition(x, y + 1 + i);
        printf("|");
        setCursorPosition(x + width + 1, y + 1 + i);
        printf("|");
    }

    setCursorPosition(x, y + height + 1);
    printf("+");
    for (i = 0; i < width; i++) printf("-");
    printf("+");
    setConsoleColor(COLOR_DEFAULT);
}

void drawMap() {
    int i, j;
    Map *m = &maps[currentMap];

    for (i = 0; i < m->height; i++) {
        setCursorPosition(2, 3 + i);
        for (j = 0; j < m->width; j++) {
            if (m->grid[i][j] == SYMBOL_WALL) {
                setConsoleColor(COLOR_WALL);
                printf("%c", SYMBOL_WALL);
            } else {
                setConsoleColor(COLOR_EMPTY);
                printf(" ");
            }
        }
    }
    setConsoleColor(COLOR_DEFAULT);
}

void drawSnake() {
    int i;
    for (i = 0; i < snake.length; i++) {
        setCursorPosition(2 + snake.body[i].x, 3 + snake.body[i].y);
        if (i == 0) {
            setConsoleColor(COLOR_SNAKE_HEAD);
            printf("%c", SYMBOL_SNAKE_HEAD);
        } else {
            setConsoleColor(COLOR_SNAKE_BODY);
            printf("%c", SYMBOL_SNAKE_BODY);
        }
    }
    setConsoleColor(COLOR_DEFAULT);
}

void drawFood() {
    int i;
    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        if (foods[i].active) {
            setCursorPosition(2 + foods[i].pos.x, 3 + foods[i].pos.y);
            setConsoleColor(COLOR_FOOD);
            printf("%c", SYMBOL_FOOD);
        }
    }
    setConsoleColor(COLOR_DEFAULT);
}

void clearSnakeTail() {
    /* Clear the entire map area and redraw everything */
    drawMap();
    drawFood();
}

void drawInfoPanel() {
    int infoX = 50;
    int i;
    Map *m = &maps[currentMap];

    setCursorPosition(infoX, 3);
    setConsoleColor(COLOR_TEXT);
    printf("=== GAME INFO ===");

    setCursorPosition(infoX, 5);
    printf("Map: %s", m->name);

    setCursorPosition(infoX, 6);
    printf("Difficulty: %s", currentMap == 0 ? "Easy" : (currentMap == 1 ? "Medium" : "Hard"));

    setCursorPosition(infoX, 8);
    setConsoleColor(14);
    printf("Score: %d", score);

    setCursorPosition(infoX, 9);
    printf("Steps: %d", steps);

    setCursorPosition(infoX, 10);
    printf("Food: %d/%d", totalFoodEaten, totalFoodOnMap);

    setCursorPosition(infoX, 12);
    setConsoleColor(COLOR_TEXT);
    printf("=== CONTROLS ===");

    setCursorPosition(infoX, 14);
    printf("W / Up    : Move Up");
    setCursorPosition(infoX, 15);
    printf("S / Down  : Move Down");
    setCursorPosition(infoX, 16);
    printf("A / Left  : Move Left");
    setCursorPosition(infoX, 17);
    printf("D / Right : Move Right");

    setCursorPosition(infoX, 19);
    printf("P         : Pause");
    setCursorPosition(infoX, 20);
    printf("Q / ESC   : Quit");

    setCursorPosition(infoX, 22);
    printf("=== LEGEND ===");
    setCursorPosition(infoX, 24);
    setConsoleColor(COLOR_SNAKE_HEAD);
    printf("%c", SYMBOL_SNAKE_HEAD);
    setConsoleColor(COLOR_TEXT);
    printf(" Snake Head");

    setCursorPosition(infoX, 25);
    setConsoleColor(COLOR_SNAKE_BODY);
    printf("%c", SYMBOL_SNAKE_BODY);
    setConsoleColor(COLOR_TEXT);
    printf(" Snake Body");

    setCursorPosition(infoX, 26);
    setConsoleColor(COLOR_FOOD);
    printf("%c", SYMBOL_FOOD);
    setConsoleColor(COLOR_TEXT);
    printf(" Food");

    setCursorPosition(infoX, 27);
    setConsoleColor(COLOR_WALL);
    printf("%c", SYMBOL_WALL);
    setConsoleColor(COLOR_TEXT);
    printf(" Wall");

    setConsoleColor(COLOR_DEFAULT);
}

void drawGameScreen() {
    clearScreen();
    setConsoleColor(COLOR_TEXT);
    setCursorPosition(2, 1);
    printf("SNAKE GAME - %s", maps[currentMap].name);
    drawMap();
    drawFood();
    drawSnake();
    drawInfoPanel();
}

/* ==================== GAME LOGIC ==================== */
int isValidPosition(int x, int y) {
    int i;
    Map *m = &maps[currentMap];

    if (x < 0 || x >= m->width || y < 0 || y >= m->height)
        return 0;

    if (m->grid[y][x] == SYMBOL_WALL)
        return 0;

    for (i = 0; i < snake.length; i++) {
        if (snake.body[i].x == x && snake.body[i].y == y)
            return 0;
    }

    return 1;
}

int isFoodPosition(int x, int y) {
    int i;
    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        if (foods[i].active && foods[i].pos.x == x && foods[i].pos.y == y)
            return 1;
    }
    return 0;
}

void spawnFood() {
    int i;
    Map *m = &maps[currentMap];

    for (i = 0; i < m->foodCount; i++) {
        if (!foods[i].active) {
            int x, y;
            do {
                x = rand() % (m->width - 2) + 1;
                y = rand() % (m->height - 2) + 1;
            } while (!isValidPosition(x, y) || isFoodPosition(x, y));

            foods[i].pos.x = x;
            foods[i].pos.y = y;
            foods[i].active = 1;
            foods[i].value = 10;
            break;
        }
    }
}

void initializeGame() {
    int i;
    Map *m = &maps[currentMap];

    /* Initialize snake in the center */
    snake.length = 3;
    snake.body[0].x = m->width / 2;
    snake.body[0].y = m->height / 2;
    snake.body[1].x = m->width / 2 - 1;
    snake.body[1].y = m->height / 2;
    snake.body[2].x = m->width / 2 - 2;
    snake.body[2].y = m->height / 2;
    snake.direction = 1; /* Right */
    snake.nextDirection = 1;

    /* Initialize foods */
    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        foods[i].active = 0;
    }

    totalFoodOnMap = m->foodCount * 3; /* Need to eat 3 rounds of food */
    totalFoodEaten = 0;
    score = 0;
    steps = 0;
    gameRunning = 1;
    gamePaused = 0;

    /* Spawn initial food */
    for (i = 0; i < m->foodCount; i++) {
        spawnFood();
    }
}

int moveSnake() {
    int i;
    Position newHead;
    int ateFood = -1;

    /* Update direction */
    if (snake.nextDirection != -1) {
        /* Prevent 180-degree turns */
        if (!((snake.direction == 0 && snake.nextDirection == 2) ||
              (snake.direction == 2 && snake.nextDirection == 0) ||
              (snake.direction == 1 && snake.nextDirection == 3) ||
              (snake.direction == 3 && snake.nextDirection == 1))) {
            snake.direction = snake.nextDirection;
        }
    }

    /* Calculate new head position */
    newHead = snake.body[0];
    switch (snake.direction) {
        case 0: newHead.y--; break; /* Up */
        case 1: newHead.x++; break; /* Right */
        case 2: newHead.y++; break; /* Down */
        case 3: newHead.x--; break; /* Left */
    }

    /* Check wall collision */
    if (!isValidPosition(newHead.x, newHead.y)) {
        return 0; /* Game over */
    }

    /* Check self collision (excluding tail which will move) */
    for (i = 0; i < snake.length - 1; i++) {
        if (snake.body[i].x == newHead.x && snake.body[i].y == newHead.y) {
            return 0; /* Game over */
        }
    }

    /* Check food collision */
    for (i = 0; i < MAX_FOOD_COUNT; i++) {
        if (foods[i].active && foods[i].pos.x == newHead.x && foods[i].pos.y == newHead.y) {
            ateFood = i;
            break;
        }
    }

    /* Move body */
    if (ateFood == -1) {
        /* Normal move - shift body */
        for (i = snake.length - 1; i > 0; i--) {
            snake.body[i] = snake.body[i - 1];
        }
        snake.body[0] = newHead;
    } else {
        /* Grow snake */
        snake.length++;
        for (i = snake.length - 1; i > 0; i--) {
            snake.body[i] = snake.body[i - 1];
        }
        snake.body[0] = newHead;

        /* Remove eaten food */
        foods[ateFood].active = 0;
        score += foods[ateFood].value;
        totalFoodEaten++;

        /* Spawn new food */
        spawnFood();
    }

    steps++;
    return 1;
}

/* ==================== SCREENS ==================== */
void showTitleScreen() {
    int i;
    clearScreen();
    setConsoleColor(COLOR_TEXT);

    setCursorPosition(20, 5);
    printf("========================================");
    setCursorPosition(20, 6);
    printf("||          S N A K E   G A M E       ||");
    setCursorPosition(20, 7);
    printf("========================================");

    setCursorPosition(20, 10);
    printf("A classic arcade game implemented in C");
    setCursorPosition(20, 11);
    printf("Navigate the snake, eat food, grow long!");
    setCursorPosition(20, 12);
    printf("Avoid walls and your own tail.");

    setCursorPosition(20, 15);
    setConsoleColor(COLOR_FOOD);
    printf("    ****    ");
    setCursorPosition(20, 16);
    printf("   *    *   ");
    setCursorPosition(20, 17);
    printf("   * oo *   ");
    setCursorPosition(20, 18);
    printf("   * oo *   ");
    setCursorPosition(20, 19);
    printf("    ****    ");
    setConsoleColor(COLOR_TEXT);

    setCursorPosition(20, 22);
    printf("Press any key to continue...");
}

void showMapSelection() {
    int i;
    int choice;
    clearScreen();

    setCursorPosition(20, 3);
    printf("========================================");
    setCursorPosition(20, 4);
    printf("||      SELECT MAP / DIFFICULTY       ||");
    setCursorPosition(20, 5);
    printf("========================================");

    for (i = 0; i < MAX_MAPS; i++) {
        setCursorPosition(20, 8 + i * 4);
        printf("[%d] %s", i + 1, maps[i].name);
        setCursorPosition(22, 9 + i * 4);
        printf("Size: %dx%d | Food: %d | Speed: %s",
               maps[i].width, maps[i].height, maps[i].foodCount,
               i == 0 ? "Slow" : (i == 1 ? "Normal" : "Fast"));
        setCursorPosition(22, 10 + i * 4);
        printf("%s", maps[i].description);
    }

    setCursorPosition(20, 22);
    printf("Enter your choice (1-3): ");

    do {
        choice = _getch() - '0';
    } while (choice < 1 || choice > 3);

    currentMap = choice - 1;
}

void showGameOverScreen(int won) {
    clearScreen();
    setConsoleColor(COLOR_TEXT);

    setCursorPosition(25, 8);
    if (won) {
        setConsoleColor(10);
        printf("*** CONGRATULATIONS! ***");
    } else {
        setConsoleColor(12);
        printf("*** GAME OVER ***");
    }
    setConsoleColor(COLOR_TEXT);

    setCursorPosition(25, 11);
    printf("Final Score: %d", score);
    setCursorPosition(25, 12);
    printf("Total Steps: %d", steps);
    setCursorPosition(25, 13);
    printf("Snake Length: %d", snake.length);
    setCursorPosition(25, 14);
    printf("Food Eaten: %d/%d", totalFoodEaten, totalFoodOnMap);

    setCursorPosition(25, 17);
    printf("Press [R] to Restart");
    setCursorPosition(25, 18);
    printf("Press [M] for Main Menu");
    setCursorPosition(25, 19);
    printf("Press [Q] to Quit");
}

void showPauseScreen() {
    setCursorPosition(20, 12);
    setConsoleColor(14);
    printf("*** GAME PAUSED ***");
    setCursorPosition(20, 14);
    printf("Press [P] to Resume");
    setCursorPosition(20, 15);
    printf("Press [Q] to Quit to Menu");
    setConsoleColor(COLOR_DEFAULT);
}

void clearPauseScreen() {
    setCursorPosition(20, 12);
    printf("                   ");
    setCursorPosition(20, 14);
    printf("                       ");
    setCursorPosition(20, 15);
    printf("                         ");
}

/* ==================== MAIN GAME LOOP ==================== */
void gameLoop() {
    int key;
    int running = 1;
    int gameOver = 0;
    int won = 0;

    drawGameScreen();

    while (running) {
        if (_kbhit()) {
            key = _getch();

            /* Handle special keys (arrow keys) */
            if (key == 224 || key == 0) {
                key = _getch();
                switch (key) {
                    case 72: snake.nextDirection = 0; break; /* Up arrow */
                    case 77: snake.nextDirection = 1; break; /* Right arrow */
                    case 80: snake.nextDirection = 2; break; /* Down arrow */
                    case 75: snake.nextDirection = 3; break; /* Left arrow */
                }
            } else {
                switch (key) {
                    case 'w': case 'W': snake.nextDirection = 0; break;
                    case 'd': case 'D': snake.nextDirection = 1; break;
                    case 's': case 'S': snake.nextDirection = 2; break;
                    case 'a': case 'A': snake.nextDirection = 3; break;
                    case 'p': case 'P':
                        gamePaused = !gamePaused;
                        if (gamePaused) {
                            showPauseScreen();
                        } else {
                            clearPauseScreen();
                        }
                        break;
                    case 'q': case 'Q': case 27:
                        running = 0;
                        break;
                }
            }
        }

        if (gamePaused || !gameRunning) {
            Sleep(50);
            continue;
        }

        /* Move snake */
        if (!moveSnake()) {
            gameOver = 1;
            running = 0;
        }

        /* Check win condition */
        if (totalFoodEaten >= totalFoodOnMap) {
            won = 1;
            gameOver = 1;
            running = 0;
        }

        /* Update display */
        if (running) {
            clearSnakeTail();
            drawSnake();
            drawInfoPanel();
        }

        Sleep(maps[currentMap].speed);
    }

    if (gameOver) {
        showGameOverScreen(won);

        while (1) {
            key = _getch();
            if (key == 'r' || key == 'R') {
                initializeGame();
                gameLoop();
                return;
            } else if (key == 'm' || key == 'M') {
                return;
            } else if (key == 'q' || key == 'Q' || key == 27) {
                exit(0);
            }
        }
    }
}

/* ==================== MAIN FUNCTION ==================== */
int main() {
    int running = 1;
    int key;

    /* Initialize */
    srand((unsigned)time(NULL));
    hideCursor();
    initializeMaps();

    while (running) {
        showTitleScreen();
        _getch();

        showMapSelection();
        initializeGame();
        gameLoop();

        /* After game loop, ask if want to play again */
        clearScreen();
        setCursorPosition(25, 10);
        printf("Thanks for playing Snake Game!");
        setCursorPosition(25, 12);
        printf("Press [Enter] to return to Main Menu");
        setCursorPosition(25, 13);
        printf("Press [Q] to Exit");

        key = _getch();
        if (key == 'q' || key == 'Q' || key == 27) {
            running = 0;
        }
    }

    clearScreen();
    setCursorPosition(25, 12);
    printf("Goodbye! Thanks for playing!");
    setCursorPosition(0, 25);

    return 0;
}
