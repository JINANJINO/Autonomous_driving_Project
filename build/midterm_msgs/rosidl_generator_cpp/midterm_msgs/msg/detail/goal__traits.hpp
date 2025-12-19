// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from midterm_msgs:msg/Goal.idl
// generated code does not contain a copyright notice

#ifndef MIDTERM_MSGS__MSG__DETAIL__GOAL__TRAITS_HPP_
#define MIDTERM_MSGS__MSG__DETAIL__GOAL__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "midterm_msgs/msg/detail/goal__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace midterm_msgs
{

namespace msg
{

inline void to_flow_style_yaml(
  const Goal & msg,
  std::ostream & out)
{
  out << "{";
  // member: x
  {
    out << "x: ";
    rosidl_generator_traits::value_to_yaml(msg.x, out);
    out << ", ";
  }

  // member: y
  {
    out << "y: ";
    rosidl_generator_traits::value_to_yaml(msg.y, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Goal & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: x
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "x: ";
    rosidl_generator_traits::value_to_yaml(msg.x, out);
    out << "\n";
  }

  // member: y
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "y: ";
    rosidl_generator_traits::value_to_yaml(msg.y, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Goal & msg, bool use_flow_style = false)
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
  const midterm_msgs::msg::Goal & msg,
  std::ostream & out, size_t indentation = 0)
{
  midterm_msgs::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use midterm_msgs::msg::to_yaml() instead")]]
inline std::string to_yaml(const midterm_msgs::msg::Goal & msg)
{
  return midterm_msgs::msg::to_yaml(msg);
}

template<>
inline const char * data_type<midterm_msgs::msg::Goal>()
{
  return "midterm_msgs::msg::Goal";
}

template<>
inline const char * name<midterm_msgs::msg::Goal>()
{
  return "midterm_msgs/msg/Goal";
}

template<>
struct has_fixed_size<midterm_msgs::msg::Goal>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<midterm_msgs::msg::Goal>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<midterm_msgs::msg::Goal>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // MIDTERM_MSGS__MSG__DETAIL__GOAL__TRAITS_HPP_
