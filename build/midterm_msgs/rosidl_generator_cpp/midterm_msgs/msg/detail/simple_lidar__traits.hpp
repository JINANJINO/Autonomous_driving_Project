// generated from rosidl_generator_cpp/resource/idl__traits.hpp.em
// with input from midterm_msgs:msg/SimpleLidar.idl
// generated code does not contain a copyright notice

#ifndef MIDTERM_MSGS__MSG__DETAIL__SIMPLE_LIDAR__TRAITS_HPP_
#define MIDTERM_MSGS__MSG__DETAIL__SIMPLE_LIDAR__TRAITS_HPP_

#include <stdint.h>

#include <sstream>
#include <string>
#include <type_traits>

#include "midterm_msgs/msg/detail/simple_lidar__struct.hpp"
#include "rosidl_runtime_cpp/traits.hpp"

namespace midterm_msgs
{

namespace msg
{

inline void to_flow_style_yaml(
  const SimpleLidar & msg,
  std::ostream & out)
{
  out << "{";
  // member: beams
  {
    if (msg.beams.size() == 0) {
      out << "beams: []";
    } else {
      out << "beams: [";
      size_t pending_items = msg.beams.size();
      for (auto item : msg.beams) {
        rosidl_generator_traits::value_to_yaml(item, out);
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
  const SimpleLidar & msg,
  std::ostream & out, size_t indentation = 0)
{
  // member: beams
  {
    if (indentation > 0) {
      out << std::string(indentation, ' ');
    }
    if (msg.beams.size() == 0) {
      out << "beams: []\n";
    } else {
      out << "beams:\n";
      for (auto item : msg.beams) {
        if (indentation > 0) {
          out << std::string(indentation, ' ');
        }
        out << "- ";
        rosidl_generator_traits::value_to_yaml(item, out);
        out << "\n";
      }
    }
  }
}  // NOLINT(readability/fn_size)

inline std::string to_yaml(const SimpleLidar & msg, bool use_flow_style = false)
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
  const midterm_msgs::msg::SimpleLidar & msg,
  std::ostream & out, size_t indentation = 0)
{
  midterm_msgs::msg::to_block_style_yaml(msg, out, indentation);
}

[[deprecated("use midterm_msgs::msg::to_yaml() instead")]]
inline std::string to_yaml(const midterm_msgs::msg::SimpleLidar & msg)
{
  return midterm_msgs::msg::to_yaml(msg);
}

template<>
inline const char * data_type<midterm_msgs::msg::SimpleLidar>()
{
  return "midterm_msgs::msg::SimpleLidar";
}

template<>
inline const char * name<midterm_msgs::msg::SimpleLidar>()
{
  return "midterm_msgs/msg/SimpleLidar";
}

template<>
struct has_fixed_size<midterm_msgs::msg::SimpleLidar>
  : std::integral_constant<bool, false> {};

template<>
struct has_bounded_size<midterm_msgs::msg::SimpleLidar>
  : std::integral_constant<bool, false> {};

template<>
struct is_message<midterm_msgs::msg::SimpleLidar>
  : std::true_type {};

}  // namespace rosidl_generator_traits

#endif  // MIDTERM_MSGS__MSG__DETAIL__SIMPLE_LIDAR__TRAITS_HPP_
