// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from midterm_msgs:msg/Control.idl
// generated code does not contain a copyright notice

#ifndef MIDTERM_MSGS__MSG__DETAIL__CONTROL__TRAITS_HPP_
#define MIDTERM_MSGS__MSG__DETAIL__CONTROL__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "midterm_msgs/msg/detail/control__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace midterm_msgs
{

namespace msg
{

inline void to_flow_style_yaml(
  const Control & msg,
  std::ostream & out)
{
  out << "{";
  // member: accel
  {
    out << "accel: ";
    rosidl_generator_traits::value_to_yaml(msg.accel, out);
    out << ", ";
  }

  // member: steering
  {
    out << "steering: ";
    rosidl_generator_traits::value_to_yaml(msg.steering, out);
  }
  out << "}";
}  // NOLINT(readability/fn_size)

inline void to_block_style_yaml(
  const Control & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: accel
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "accel: ";
    rosidl_generator_traits::value_to_yaml(msg.accel, out);
    out << "\n";
  }

  // member: steering
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    out << "steering: ";
    rosidl_generator_traits::value_to_yaml(msg.steering, out);
    out << "\n";
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const Control & msg, bool use_flow_style = false)
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
  const midterm_msgs::msg::Control & msg,
  std::ostream & out, size_t indentation = 0)
{
  midterm_msgs::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use midterm_msgs::msg::to_yaml() instead")]]
inline std::string to_yaml(const midterm_msgs::msg::Control & msg)
{
  return midterm_msgs::msg::to_yaml(msg);
}

template<>
inline const char * data_type<midterm_msgs::msg::Control>()
{
  return "midterm_msgs::msg::Control";
}

template<>
inline const char * name<midterm_msgs::msg::Control>()
{
  return "midterm_msgs/msg/Control";
}

template<>
struct has_fixed_size<midterm_msgs::msg::Control>
  : std::integral_constant<bool, true> {};

template<>
struct has_bounded_size<midterm_msgs::msg::Control>
  : std::integral_constant<bool, true> {};

template<>
struct is_message<midterm_msgs::msg::Control>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // MIDTERM_MSGS__MSG__DETAIL__CONTROL__TRAITS_HPP_
