#include <iostream>
#include <string>
extern int managed_answer();
int main() {
    const std::string message = "managed GCC consumer";
    std::cout << message << ": " << managed_answer() << std::endl;
    return managed_answer() == 42 ? 0 : 1;
}
