// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from midterm_msgs:msg/WallList.idl
// generated code does not contain a copyright notice

#ifndef MIDTERM_MSGS__MSG__DETAIL__WALL_LIST__TRAITS_HPP_
#define MIDTERM_MSGS__MSG__DETAIL__WALL_LIST__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "midterm_msgs/msg/detail/wall_list__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

// Include directives for member types
// Member 'walls'
#include "midterm_msgs/msg/detail/wall__traits.hpp"

namespace midterm_msgs
{

namespace msg
{

inline void to_flow_style_yaml(
  const WallList & msg,
  std::ostream & out)
{
  out << "{";
  // member: walls
  {
    if (msg.walls.size() == 0) {
      out << "walls: []";
    } else {
      out << "walls: [";
      size_t pending_items = msg.walls.size();
      for (auto item : msg.walls) {
        to_flow_style_yaml(item, out);
        if (--pending_items > 0) {
          out << ", ";
        }
      }
      out << "]";
    }
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const WallList & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: walls
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.walls.size() == 0) {
      out << "walls: []\n";
    } else {
      out << "walls:\n";
      for (auto item : msg.walls) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "-\n";
        to_block_style_yaml(item, out, indentation + 2);
      }
    }
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const WallList & msg, bool use_flow_style = false)
{
  std::ostringstream out;
  if (use_flow_style) {
    to_flow_style_yaml(msg, out);
  } else {
    to_block_style_yaml(msg, out);
  }
  return out.str();
}

}  // namespace msg

}  // namespace midterm_msgs

namespace rosidl_generator_traits
{

[[deprecated("use midterm_msgs::msg::to_block_style_yaml() instead")]]
inline void to_yaml(
  const midterm_msgs::msg::WallList & msg,
  std::ostream & out, size_t indentation = 0)
{
  midterm_msgs::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use midterm_msgs::msg::to_yaml() instead")]]
inline std::string to_yaml(const midterm_msgs::msg::WallList & msg)
{
  return midterm_msgs::msg::to_yaml(msg);
}

template<>
inline const char * data_type<midterm_msgs::msg::WallList>()
{
  return "midterm_msgs::msg::WallList";
}

template<>
inline const char * name<midterm_msgs::msg::WallList>()
{
  return "midterm_msgs/msg/WallList";
}

template<>
struct has_fixed_size<midterm_msgs::msg::WallList>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<midterm_msgs::msg::WallList>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<midterm_msgs::msg::WallList>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // MIDTERM_MSGS__MSG__DETAIL__WALL_LIST__TRAITS_HPP_
