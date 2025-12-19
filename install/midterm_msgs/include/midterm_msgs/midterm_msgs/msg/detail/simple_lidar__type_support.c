// generated from rosidl_typesupport_introspection_c/resource/idl__type_support.c.em
// with input from midterm_msgs:msg/SimpleLidar.idl
// generated code does not contain a copyright notice

#include <stddef.h>
#include "midterm_msgs/msg/detail/simple_lidar__rosidl_typesupport_introspection_c.h"
#include "midterm_msgs/msg/rosidl_typesupport_introspection_c__visibility_control.h"
#include "rosidl_typesupport_introspection_c/field_types.h"
#include "rosidl_typesupport_introspection_c/identifier.h"
#include "rosidl_typesupport_introspection_c/message_introspection.h"
#include "midterm_msgs/msg/detail/simple_lidar__functions.h"
#include "midterm_msgs/msg/detail/simple_lidar__struct.h"


// Include directives for member types
// Member `beams`
#include "rosidl_runtime_c/primitives_sequence_functions.h"

#ifdef __cplusplus
extern "C"
{
#endif

void midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_init_function(
  void * message_memory, enum rosidl_runtime_c__message_initialization _init)
{
  // TODO(karsten1987): initializers are not yet implemented for typesupport c
  // see https://github.com/ros2/ros2/issues/397
  (void) _init;
  midterm_msgs__msg__SimpleLidar__init(message_memory);
}

void midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_fini_function(void * message_memory)
{
  midterm_msgs__msg__SimpleLidar__fini(message_memory);
}

size_t midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__size_function__SimpleLidar__beams(
  const void * untyped_member)
{
  const rosidl_runtime_c__float__Sequence * member =
    (const rosidl_runtime_c__float__Sequence *)(untyped_member);
  return member->size;
}

const void * midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__get_const_function__SimpleLidar__beams(
  const void * untyped_member, size_t index)
{
  const rosidl_runtime_c__float__Sequence * member =
    (const rosidl_runtime_c__float__Sequence *)(untyped_member);
  return &member->data[index];
}

void * midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__get_function__SimpleLidar__beams(
  void * untyped_member, size_t index)
{
  rosidl_runtime_c__float__Sequence * member =
    (rosidl_runtime_c__float__Sequence *)(untyped_member);
  return &member->data[index];
}

void midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__fetch_function__SimpleLidar__beams(
  const void * untyped_member, size_t index, void * untyped_value)
{
  const float * item =
    ((const float *)
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__get_const_function__SimpleLidar__beams(untyped_member, index));
  float * value =
    (float *)(untyped_value);
  *value = *item;
}

void midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__assign_function__SimpleLidar__beams(
  void * untyped_member, size_t index, const void * untyped_value)
{
  float * item =
    ((float *)
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__get_function__SimpleLidar__beams(untyped_member, index));
  const float * value =
    (const float *)(untyped_value);
  *item = *value;
}

bool midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__resize_function__SimpleLidar__beams(
  void * untyped_member, size_t size)
{
  rosidl_runtime_c__float__Sequence * member =
    (rosidl_runtime_c__float__Sequence *)(untyped_member);
  rosidl_runtime_c__float__Sequence__fini(member);
  return rosidl_runtime_c__float__Sequence__init(member, size);
}

static rosidl_typesupport_introspection_c__MessageMember midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_message_member_array[1] = {
  {
    "beams",  // name
    rosidl_typesupport_introspection_c__ROS_TYPE_FLOAT,  // type
    0,  // upper bound of string
    NULL,  // members of sub message
    true,  // is array
    0,  // array size
    false,  // is upper bound
    offsetof(midterm_msgs__msg__SimpleLidar, beams),  // bytes offset in struct
    NULL,  // default value
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__size_function__SimpleLidar__beams,  // size() function pointer
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__get_const_function__SimpleLidar__beams,  // get_const(index) function pointer
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__get_function__SimpleLidar__beams,  // get(index) function pointer
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__fetch_function__SimpleLidar__beams,  // fetch(index, &value) function pointer
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__assign_function__SimpleLidar__beams,  // assign(index, value) function pointer
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__resize_function__SimpleLidar__beams  // resize(index) function pointer
  }
};

static const rosidl_typesupport_introspection_c__MessageMembers midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_message_members = {
  "midterm_msgs__msg",  // message namespace
  "SimpleLidar",  // message name
  1,  // number of fields
  sizeof(midterm_msgs__msg__SimpleLidar),
  midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_message_member_array,  // message members
  midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_init_function,  // function to initialize message memory (memory has to be allocated)
  midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_fini_function  // function to terminate message instance (will not free memory)
};

// this is not const since it must be initialized on first access
// since C does not allow non-integral compile-time constants
static rosidl_message_type_support_t midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_message_type_support_handle = {
  0,
  &midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_message_members,
  get_message_typesupport_handle_function,
};

ROSIDL_TYPESUPPORT_INTROSPECTION_C_EXPORT_midterm_msgs
const rosidl_message_type_support_t *
ROSIDL_TYPESUPPORT_INTERFACE__MESSAGE_SYMBOL_NAME(rosidl_typesupport_introspection_c, midterm_msgs, msg, SimpleLidar)() {
  if (!midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_message_type_support_handle.typesupport_identifier) {
    midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_message_type_support_handle.typesupport_identifier =
      rosidl_typesupport_introspection_c__identifier;
  }
  return &midterm_msgs__msg__SimpleLidar__rosidl_typesupport_introspection_c__SimpleLidar_message_type_support_handle;
}
#ifdef __cplusplus
}
#endif
