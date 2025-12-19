// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from midterm_msgs:msg/Wall.idl
// generated code does not contain a copyright notice

#ifndef MIDTERM_MSGS__MSG__DETAIL__WALL__TRAITS_HPP_
#define MIDTERM_MSGS__MSG__DETAIL__WALL__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "midterm_msgs/msg/detail/wall__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace midterm_msgs
{

namespace msg
{

inline void to_flow_style_yaml(
  const Wall & msg,
  std::ostream & out)
{
  out << "{";
  // member: bl_x
  {
    out << "bl_x: ";
    rosidl_generator_traits::value_to_yaml(msg.bl_x, out);
    out << ", ";
  }

  // member: bl_y
  {
    out << "bl_y: ";
    rosidl_generator_traits::value_to_yaml(msg.bl_y, out);
    out << ", ";
  }

  // member: size_x
  {
    out << "size_x: ";
    rosidl_generator_traits::value_to_yaml(msg.size_x, out);
    out << ", ";
  }

  // member: size_y
  {
    out << "size_y: ";
    rosidl_generator_traits::value_to_yaml(msg.size_y, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Wall & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: bl_x
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bl_x: ";
    rosidl_generator_traits::value_to_yaml(msg.bl_x, out);
    out << "\n";
  }

  // member: bl_y
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "bl_y: ";
    rosidl_generator_traits::value_to_yaml(msg.bl_y, out);
    out << "\n";
  }

  // member: size_x
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "size_x: ";
    rosidl_generator_traits::value_to_yaml(msg.size_x, out);
    out << "\n";
  }

  // member: size_y
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "size_y: ";
    rosidl_generator_traits::value_to_yaml(msg.size_y, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Wall & msg, bool use_flow_style = false)
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
  const midterm_msgs::msg::Wall & msg,
  std::ostream & out, size_t indentation = 0)
{
  midterm_msgs::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use midterm_msgs::msg::to_yaml() instead")]]
inline std::string to_yaml(const midterm_msgs::msg::Wall & msg)
{
  return midterm_msgs::msg::to_yaml(msg);
}

template<>
inline const char * data_type<midterm_msgs::msg::Wall>()
{
  return "midterm_msgs::msg::Wall";
}

template<>
inline const char * name<midterm_msgs::msg::Wall>()
{
  return "midterm_msgs/msg/Wall";
}

template<>
struct has_fixed_size<midterm_msgs::msg::Wall>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<midterm_msgs::msg::Wall>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<midterm_msgs::msg::Wall>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // MIDTERM_MSGS__MSG__DETAIL__WALL__TRAITS_HPP_
