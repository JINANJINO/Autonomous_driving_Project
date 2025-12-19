import rclpy
from rclpy.node import Node
import curses  # curses 라이브러리 사용
from midterm_msgs.msg import Control

class KeyboardController(Node):
    def __init__(self):
        super().__init__('keyboard_controller')
        self.publisher_ = self.create_publisher(Control, '/control', 10)
        self.get_logger().info('Keyboard Controller Node started. Use W/A/S/D keys to control, Q to quit.')
        self.acceleration = 0.0  # m/s^2
        self.steering_angle = 0.0  # degrees

    def publish_cmd(self):
        msg = Control()
        msg.accel = self.acceleration
        msg.steering = self.steering_angle
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published -> Acceleration: {self.acceleration:.2f}, Steering Angle: {self.steering_angle:.2f}')

    def run(self, stdscr):
        # curses 설정 초기화
        curses.cbreak()
        stdscr.nodelay(True)  # 입력이 없을 때 blocking되지 않도록 설정
        stdscr.clear()
        stdscr.addstr(0, 0, "Control the vehicle with W/A/S/D keys. Press Q to quit.")

        try:
            while rclpy.ok():
                key = stdscr.getch()  # 키 입력 읽기
                if key == ord('w'):  # W 키
                    self.acceleration += 0.1
                elif key == ord('s'):  # S 키
                    self.acceleration -= 0.1
                elif key == ord('a'):  # A 키
                    self.steering_angle += 0.2
                elif key == ord('d'):  # D 키
                    self.steering_angle -= 0.2
                elif key == ord('q'):  # Q 키로 종료
                    self.get_logger().info('Exiting...')
                    break

                # 값 제한
                self.acceleration = max(-10.0, min(10.0, self.acceleration))
                self.steering_angle = max(-45.0, min(45.0, self.steering_angle))

                # 상태 표시
                stdscr.addstr(2, 0, f"Acceleration: {self.acceleration:.2f}, Steering Angle: {self.steering_angle:.2f}")
                stdscr.refresh()

                # 퍼블리시
                self.publish_cmd()

                # 루프 속도 조절 (0.1초)
                rclpy.spin_once(self, timeout_sec=0.1)
        except KeyboardInterrupt:
            self.get_logger().info('Interrupted by user. Shutting down.')

def main(args=None):
    rclpy.init(args=args)
    node = KeyboardController()

    # curses 래퍼로 run 실행
    curses.wrapper(node.run)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()